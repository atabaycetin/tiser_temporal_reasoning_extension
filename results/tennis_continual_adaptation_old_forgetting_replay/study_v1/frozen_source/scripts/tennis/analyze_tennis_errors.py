"""Analyze tennis-domain prediction errors across adaptation conditions."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CONDITIONS = ["base_qwen", "original_tiser", "tennis_only", "mixed_replay"]
OUTPUT_FILENAMES = {
    "summary": "error_summary.json",
    "report": "error_analysis_report.md",
    "fixed_by_tennis_only": "fixed_by_tennis_only.jsonl",
    "broken_by_tennis_only": "broken_by_tennis_only.jsonl",
    "fixed_by_mixed_replay": "fixed_by_mixed_replay.jsonl",
    "persistent_failures": "persistent_failures.jsonl",
}
EXAMPLE_LIMIT = 8
RAW_EXCERPT_CHARS = 500


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    predictions_root = resolve_repo_path(args.predictions_root)
    output_dir = resolve_repo_path(args.output_dir)
    outputs = {name: output_dir / filename for name, filename in OUTPUT_FILENAMES.items()}
    guard_outputs(outputs, force=args.force)

    condition_rows = load_available_predictions(predictions_root)
    available = [condition for condition in CONDITIONS if condition in condition_rows]
    missing = [condition for condition in CONDITIONS if condition not in condition_rows]
    grouped = group_by_question(condition_rows)

    analysis = build_analysis(condition_rows, grouped, available, missing, args.predictions_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(outputs["summary"], analysis["summary"])
    write_text(outputs["report"], render_report(analysis))
    write_jsonl(outputs["fixed_by_tennis_only"], analysis["fixed_by_tennis_only"])
    write_jsonl(outputs["broken_by_tennis_only"], analysis["broken_by_tennis_only"])
    write_jsonl(outputs["fixed_by_mixed_replay"], analysis["fixed_by_mixed_replay"])
    write_jsonl(outputs["persistent_failures"], analysis["persistent_failures"])

    print("[tennis-errors] available conditions: " + (", ".join(available) if available else "none"))
    print("[tennis-errors] missing conditions: " + (", ".join(missing) if missing else "none"))
    print("[tennis-errors] wrote:")
    for path in outputs.values():
        print(f"- {relative_path(path)}")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare tennis prediction errors across adapter conditions."
    )
    parser.add_argument(
        "--predictions-root",
        default="results/tennis_domain_adaptation/scored",
        help="Directory containing <condition>/predictions.jsonl files.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/tennis_domain_adaptation/comparisons/error_analysis",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing error-analysis outputs.",
    )
    return parser.parse_args(argv)


def guard_outputs(outputs: dict[str, Path], *, force: bool) -> None:
    existing = [path for path in outputs.values() if path.exists()]
    if existing and not force:
        joined = ", ".join(relative_path(path) for path in existing)
        raise FileExistsError(f"Error-analysis outputs exist ({joined}); pass --force.")


def load_available_predictions(predictions_root: Path) -> dict[str, list[dict[str, Any]]]:
    loaded: dict[str, list[dict[str, Any]]] = {}
    for condition in CONDITIONS:
        path = predictions_root / condition / "predictions.jsonl"
        if path.exists():
            loaded[condition] = load_jsonl(path)
    return loaded


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            if not isinstance(row, dict):
                raise ValueError(f"Line {line_number} of {path} is not a JSON object.")
            row["_source_path"] = relative_path(path)
            rows.append(row)
    return rows


def group_by_question(
    condition_rows: dict[str, list[dict[str, Any]]]
) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for condition, rows in condition_rows.items():
        for index, row in enumerate(rows, start=1):
            question_id = str(row.get("question_id") or f"{condition}_{index:05d}")
            grouped[question_id][condition] = normalize_row(row, condition, question_id)
    return dict(grouped)


def normalize_row(row: dict[str, Any], condition: str, question_id: str) -> dict[str, Any]:
    prompt = str(row.get("prompt") or "")
    context, question = context_question(row, prompt)
    gold = str(row.get("gold", row.get("answer", "")))
    pred = str(row.get("pred_answer", row.get("prediction", "")))
    em = row.get("em")
    f1 = row.get("f1")
    correct = bool(float(em)) if is_number(em) else normalize_answer(pred) == normalize_answer(gold)
    return {
        "condition": condition,
        "question_id": question_id,
        "dataset_name": row.get("dataset_name", ""),
        "category": str(row.get("category") or "unknown"),
        "context": context,
        "question": question,
        "prompt": prompt,
        "gold": gold,
        "pred_answer": pred,
        "raw_generation": str(row.get("raw_generation") or ""),
        "raw_generation_excerpt": excerpt(row.get("raw_generation") or ""),
        "malformed": bool(row.get("malformed", False)),
        "em": float(em) if is_number(em) else float(correct),
        "f1": float(f1) if is_number(f1) else token_f1(pred, gold),
        "correct": correct,
        "source_path": row.get("_source_path", ""),
    }


def build_analysis(
    condition_rows: dict[str, list[dict[str, Any]]],
    grouped: dict[str, dict[str, dict[str, Any]]],
    available: list[str],
    missing: list[str],
    predictions_root_arg: str,
) -> dict[str, Any]:
    overview = build_overview(condition_rows)
    category_errors = build_category_errors(condition_rows)
    malformed_by_condition = {
        condition: {
            "malformed": sum(1 for row in rows if bool(row.get("malformed", False))),
            "total": len(rows),
            "malformed_rate": safe_rate(
                sum(1 for row in rows if bool(row.get("malformed", False))), len(rows)
            ),
        }
        for condition, rows in condition_rows.items()
    }

    fixed_by_tennis_only = transition_examples(
        grouped,
        from_condition="original_tiser",
        to_condition="tennis_only",
        from_correct=False,
        to_correct=True,
        available=available,
    )
    broken_by_tennis_only = transition_examples(
        grouped,
        from_condition="original_tiser",
        to_condition="tennis_only",
        from_correct=True,
        to_correct=False,
        available=available,
    )
    fixed_by_mixed_replay = transition_examples(
        grouped,
        from_condition="tennis_only",
        to_condition="mixed_replay",
        from_correct=False,
        to_correct=True,
        available=available,
    )
    persistent_failures = persistent_failure_examples(grouped, available)

    failure_mode_counts = build_failure_mode_counts(grouped, available)
    summary = {
        "predictions_root": predictions_root_arg,
        "available_conditions": available,
        "missing_conditions": missing,
        "n_questions": len(grouped),
        "overview_by_condition": overview,
        "category_errors": category_errors,
        "malformed_by_condition": malformed_by_condition,
        "transitions": {
            "fixed_by_tennis_only": len(fixed_by_tennis_only),
            "broken_by_tennis_only": len(broken_by_tennis_only),
            "fixed_by_mixed_replay": len(fixed_by_mixed_replay),
            "persistent_failures": len(persistent_failures),
        },
        "suspected_failure_mode_counts": failure_mode_counts,
    }
    return {
        "summary": summary,
        "fixed_by_tennis_only": fixed_by_tennis_only,
        "broken_by_tennis_only": broken_by_tennis_only,
        "fixed_by_mixed_replay": fixed_by_mixed_replay,
        "persistent_failures": persistent_failures,
    }


def build_overview(condition_rows: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    overview = {}
    for condition, raw_rows in condition_rows.items():
        rows = [
            normalize_row(row, condition, str(row.get("question_id") or index))
            for index, row in enumerate(raw_rows, start=1)
        ]
        correct = sum(1 for row in rows if row["correct"])
        malformed = sum(1 for row in rows if row["malformed"])
        overview[condition] = {
            "total": len(rows),
            "correct": correct,
            "incorrect": len(rows) - correct,
            "em": safe_mean(row["em"] for row in rows),
            "f1": safe_mean(row["f1"] for row in rows),
            "malformed": malformed,
            "malformed_rate": safe_rate(malformed, len(rows)),
        }
    return overview


def build_category_errors(
    condition_rows: dict[str, list[dict[str, Any]]]
) -> dict[str, dict[str, dict[str, Any]]]:
    output: dict[str, dict[str, dict[str, Any]]] = {}
    for condition, raw_rows in condition_rows.items():
        rows = [
            normalize_row(row, condition, str(row.get("question_id") or index))
            for index, row in enumerate(raw_rows, start=1)
        ]
        categories = sorted({row["category"] for row in rows})
        output[condition] = {}
        for category in categories:
            category_rows = [row for row in rows if row["category"] == category]
            incorrect = sum(1 for row in category_rows if not row["correct"])
            malformed = sum(1 for row in category_rows if row["malformed"])
            output[condition][category] = {
                "total": len(category_rows),
                "incorrect": incorrect,
                "error_rate": safe_rate(incorrect, len(category_rows)),
                "malformed": malformed,
                "malformed_rate": safe_rate(malformed, len(category_rows)),
            }
    return output


def transition_examples(
    grouped: dict[str, dict[str, dict[str, Any]]],
    *,
    from_condition: str,
    to_condition: str,
    from_correct: bool,
    to_correct: bool,
    available: list[str],
) -> list[dict[str, Any]]:
    if from_condition not in available or to_condition not in available:
        return []
    examples = []
    for question_id, by_condition in sorted(grouped.items()):
        source = by_condition.get(from_condition)
        target = by_condition.get(to_condition)
        if not source or not target:
            continue
        if source["correct"] is from_correct and target["correct"] is to_correct:
            examples.append(build_qualitative_example(question_id, by_condition, available, target))
    return examples


def persistent_failure_examples(
    grouped: dict[str, dict[str, dict[str, Any]]], available: list[str]
) -> list[dict[str, Any]]:
    if not available:
        return []
    examples = []
    for question_id, by_condition in sorted(grouped.items()):
        present = [condition for condition in available if condition in by_condition]
        if present and all(not by_condition[condition]["correct"] for condition in present):
            reference = by_condition[present[-1]]
            examples.append(build_qualitative_example(question_id, by_condition, present, reference))
    return examples


def build_qualitative_example(
    question_id: str,
    by_condition: dict[str, dict[str, Any]],
    conditions: list[str],
    reference: dict[str, Any],
) -> dict[str, Any]:
    predictions = {
        condition: {
            "pred_answer": by_condition[condition]["pred_answer"],
            "correct": by_condition[condition]["correct"],
            "em": by_condition[condition]["em"],
            "f1": by_condition[condition]["f1"],
            "malformed": by_condition[condition]["malformed"],
            "raw_generation_excerpt": by_condition[condition]["raw_generation_excerpt"],
        }
        for condition in conditions
        if condition in by_condition
    }
    return {
        "question_id": question_id,
        "category": reference["category"],
        "context": reference["context"],
        "question": reference["question"],
        "gold": reference["gold"],
        "predictions": predictions,
        "raw_generation_excerpt": {
            condition: values["raw_generation_excerpt"]
            for condition, values in predictions.items()
        },
        "automatic_note": automatic_note(reference, by_condition),
    }


def build_failure_mode_counts(
    grouped: dict[str, dict[str, dict[str, Any]]], available: list[str]
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for by_condition in grouped.values():
        for condition in available:
            row = by_condition.get(condition)
            if row and not row["correct"]:
                counts.update(suspected_failure_modes(row))
    return dict(sorted(counts.items()))


def automatic_note(reference: dict[str, Any], by_condition: dict[str, dict[str, Any]]) -> str:
    modes = suspected_failure_modes(reference)
    wrong_conditions = [
        condition for condition, row in by_condition.items() if not row["correct"]
    ]
    fixed_conditions = [
        condition for condition, row in by_condition.items() if row["correct"]
    ]
    parts = []
    if modes:
        parts.append("suspected " + ", ".join(modes))
    if wrong_conditions:
        parts.append("wrong in " + ", ".join(sorted(wrong_conditions)))
    if fixed_conditions:
        parts.append("correct in " + ", ".join(sorted(fixed_conditions)))
    return "; ".join(parts) if parts else "no automatic failure-mode signal"


def suspected_failure_modes(row: dict[str, Any]) -> list[str]:
    category = row["category"]
    pred = row["pred_answer"]
    gold = row["gold"]
    context = row["context"]
    modes: list[str] = []
    if row["malformed"]:
        modes.append("malformed output")
    if category in {"yes_no_before_after", "which_first_last", "immediate_before_after", "tournament_round_sequence"}:
        modes.append("temporal order reversal")
    if category == "duration_minutes" or has_duration(gold) or has_duration(pred):
        modes.append("duration arithmetic")
    if category == "overlap_while_during":
        modes.append("overlap reasoning")
    if not row["correct"] and row["f1"] > 0 and row["em"] == 0:
        modes.append("answer formatting")
    if pred and context and normalize_answer(pred) not in normalize_answer(context) and category not in {"duration_minutes", "yes_no_before_after"}:
        modes.append("memorization/context conflict")
    return modes or ["answer formatting"]


def context_question(row: dict[str, Any], prompt: str) -> tuple[str, str]:
    context = row.get("context")
    question = row.get("question")
    if isinstance(context, str) and isinstance(question, str):
        return context, question

    extracted = extract_context_question(prompt)
    return (
        context if isinstance(context, str) and context else extracted[0],
        question if isinstance(question, str) and question else extracted[1],
    )


def extract_context_question(prompt: str) -> tuple[str, str]:
    patterns = [
        (r"Temporal context:\s*(?P<context>.*?)(?:\n\s*\nQuestion:\s*)(?P<question>.*?)(?:\n\s*\nReturn|\Z)", re.S),
        (r"Passage:\s*(?P<context>.*?)(?:\n\s*\nQuestion:\s*)(?P<question>.*?)(?:\n|\Z)", re.S),
        (r"Context:\s*(?P<context>.*?)(?:\n\s*\nQuestion:\s*)(?P<question>.*?)(?:\n|\Z)", re.S),
    ]
    for pattern, flags in patterns:
        match = re.search(pattern, prompt, flags)
        if match:
            return clean_text(match.group("context")), clean_text(match.group("question"))
    return "", ""


def normalize_answer(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\b(a|an|the)\b", " ", value)
    return " ".join(value.split())


def token_f1(pred: str, gold: str) -> float:
    pred_tokens = normalize_answer(pred).split()
    gold_tokens = normalize_answer(gold).split()
    if not pred_tokens or not gold_tokens:
        return float(pred_tokens == gold_tokens)
    overlap = Counter(pred_tokens) & Counter(gold_tokens)
    n_overlap = sum(overlap.values())
    if n_overlap == 0:
        return 0.0
    precision = n_overlap / len(pred_tokens)
    recall = n_overlap / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def has_duration(value: str) -> bool:
    return bool(re.search(r"\b\d+\s*(?:minute|minutes|min|mins)\b", value.lower()))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def safe_mean(values: Any) -> float:
    collected = [float(value) for value in values]
    return sum(collected) / len(collected) if collected else 0.0


def safe_rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def excerpt(value: Any, limit: int = RAW_EXCERPT_CHARS) -> str:
    text = clean_text(str(value))
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def clean_text(value: str) -> str:
    return " ".join(value.replace("\r", "\n").split())


def render_report(analysis: dict[str, Any]) -> str:
    summary = analysis["summary"]
    lines = [
        "# Tennis Error Analysis",
        "",
        f"- Predictions root: `{summary['predictions_root']}`",
        "- Available conditions: "
        + (", ".join(f"`{condition}`" for condition in summary["available_conditions"]) or "none"),
        "- Missing conditions: "
        + (", ".join(f"`{condition}`" for condition in summary["missing_conditions"]) or "none"),
        f"- Questions grouped: {summary['n_questions']}",
        "",
    ]
    if not summary["available_conditions"]:
        lines.extend(
            [
                "No prediction files were found. Run the planned evaluations first; missing conditions are not counted as failures.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(render_overview(summary["overview_by_condition"]))
    lines.extend(render_category_table(summary["category_errors"]))
    lines.extend(render_malformed(summary["malformed_by_condition"]))
    lines.extend(render_failure_modes(summary["suspected_failure_mode_counts"]))
    lines.extend(render_examples("Examples Fixed By Tennis Adaptation", analysis["fixed_by_tennis_only"]))
    lines.extend(render_examples("Examples Harmed By Tennis Adaptation", analysis["broken_by_tennis_only"]))
    lines.extend(render_examples("Examples Fixed By Mixed Replay", analysis["fixed_by_mixed_replay"]))
    lines.extend(render_examples("Persistent Failure Examples", analysis["persistent_failures"]))
    return "\n".join(lines)


def render_overview(overview: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        "## Overview By Condition",
        "",
        "| Condition | Total | Correct | Incorrect | EM | F1 | Malformed | Malformed Rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition in CONDITIONS:
        row = overview.get(condition)
        if not row:
            continue
        lines.append(
            f"| `{condition}` | {row['total']} | {row['correct']} | {row['incorrect']} | "
            f"{row['em']:.4f} | {row['f1']:.4f} | {row['malformed']} | {row['malformed_rate']:.4f} |"
        )
    lines.append("")
    return lines


def render_category_table(category_errors: dict[str, dict[str, dict[str, Any]]]) -> list[str]:
    lines = [
        "## Category-Wise Error Counts",
        "",
        "| Condition | Category | Total | Errors | Error Rate | Malformed | Malformed Rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition in CONDITIONS:
        for category, row in sorted(category_errors.get(condition, {}).items()):
            lines.append(
                f"| `{condition}` | `{category}` | {row['total']} | {row['incorrect']} | "
                f"{row['error_rate']:.4f} | {row['malformed']} | {row['malformed_rate']:.4f} |"
            )
    lines.append("")
    return lines


def render_malformed(malformed: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        "## Malformed Outputs",
        "",
        "| Condition | Malformed | Total | Malformed Rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for condition in CONDITIONS:
        row = malformed.get(condition)
        if row:
            lines.append(
                f"| `{condition}` | {row['malformed']} | {row['total']} | {row['malformed_rate']:.4f} |"
            )
    lines.append("")
    return lines


def render_failure_modes(counts: dict[str, int]) -> list[str]:
    expected = [
        "temporal order reversal",
        "duration arithmetic",
        "overlap reasoning",
        "answer formatting",
        "malformed output",
        "memorization/context conflict",
    ]
    lines = [
        "## Suspected Failure Modes",
        "",
        "| Failure Mode | Count |",
        "| --- | ---: |",
    ]
    for mode in expected:
        lines.append(f"| {mode} | {counts.get(mode, 0)} |")
    lines.append("")
    return lines


def render_examples(title: str, examples: list[dict[str, Any]]) -> list[str]:
    lines = [f"## {title}", ""]
    if not examples:
        lines.extend(["No examples available.", ""])
        return lines
    for example in examples[:EXAMPLE_LIMIT]:
        lines.extend(
            [
                f"### `{example['question_id']}`",
                "",
                f"- Category: `{example['category']}`",
                f"- Question: {escape_md(example['question']) or 'MISSING'}",
                f"- Gold: {escape_md(example['gold']) or 'MISSING'}",
                f"- Context: {escape_md(excerpt(example['context'], 300)) or 'MISSING'}",
                f"- Automatic note: {escape_md(example['automatic_note'])}",
                "",
                "| Condition | Correct | Prediction | Raw Generation Excerpt |",
                "| --- | --- | --- | --- |",
            ]
        )
        for condition in CONDITIONS:
            pred = example["predictions"].get(condition)
            if not pred:
                continue
            lines.append(
                f"| `{condition}` | {pred['correct']} | {escape_md(pred['pred_answer'])} | "
                f"{escape_md(pred['raw_generation_excerpt'])} |"
            )
        lines.append("")
    if len(examples) > EXAMPLE_LIMIT:
        lines.append(f"_Showing {EXAMPLE_LIMIT} of {len(examples)} examples._")
        lines.append("")
    return lines


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def escape_md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def resolve_repo_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return REPO_ROOT / value


def relative_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
