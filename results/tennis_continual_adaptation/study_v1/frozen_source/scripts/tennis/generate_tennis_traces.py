"""Prepare and validate externally generated tennis TISER traces."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tennis.trace_generation import build_trace_generation_prompt, validate_tiser_output


def load_json_array(path: Path | str) -> list[dict[str, Any]]:
    input_path = Path(path)
    data = json.loads(input_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {input_path}")
    records: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Record {index} in {input_path} is not a JSON object")
        records.append(item)
    return records


def write_json(path: Path | str, data: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path: Path | str, rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _required_string(record: dict[str, Any], key: str, *, index: int) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Record {index} is missing non-empty string field: {key}")
    return value.strip()


def extract_context_from_record(record: dict[str, Any], *, index: int) -> str:
    context = record.get("context")
    if isinstance(context, str) and context.strip():
        return context.strip()

    prompt = record.get("prompt")
    if isinstance(prompt, str):
        marker = "Temporal context:\n"
        question_marker = "\n\nQuestion:"
        if marker in prompt and question_marker in prompt:
            after_marker = prompt.split(marker, 1)[1]
            context_text = after_marker.split(question_marker, 1)[0].strip()
            if context_text:
                return context_text

    raise ValueError(
        f"Record {index} has no context field and context could not be extracted from prompt"
    )


def build_request_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        context = extract_context_from_record(record, index=index)
        question = _required_string(record, "question", index=index)
        gold_answer = _required_string(record, "answer", index=index)
        category = _required_string(record, "category", index=index)
        question_id = _required_string(record, "question_id", index=index)
        rows.append(
            {
                "question_id": question_id,
                "category": category,
                "context": context,
                "question": question,
                "gold_answer": gold_answer,
                "generation_prompt": build_trace_generation_prompt(
                    context, question, gold_answer, category
                ),
            }
        )
    return rows


def load_generation_rows(path: Path | str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    generations: dict[str, str] = {}
    load_errors: list[dict[str, Any]] = []
    input_path = Path(path)
    with input_path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                load_errors.append(
                    {
                        "line_number": line_number,
                        "errors": [f"invalid JSON: {error.msg}"],
                    }
                )
                continue
            if not isinstance(item, dict):
                load_errors.append(
                    {"line_number": line_number, "errors": ["generation row is not an object"]}
                )
                continue
            question_id = item.get("question_id")
            output = item.get("output")
            row_errors: list[str] = []
            if not isinstance(question_id, str) or not question_id.strip():
                row_errors.append("missing non-empty question_id")
            if not isinstance(output, str):
                row_errors.append("missing string output")
            if row_errors:
                load_errors.append({"line_number": line_number, "errors": row_errors})
                continue
            normalized_id = question_id.strip()
            if normalized_id in generations:
                load_errors.append(
                    {
                        "line_number": line_number,
                        "question_id": normalized_id,
                        "errors": ["duplicate question_id; keeping first generation"],
                    }
                )
                continue
            generations[normalized_id] = output
    return generations, load_errors


def validate_generations(
    base_records: list[dict[str, Any]], generations: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    filtered_records: list[dict[str, Any]] = []
    invalid_examples: list[dict[str, Any]] = []
    category_totals: Counter[str] = Counter()
    category_valid: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()

    for index, record in enumerate(base_records, start=1):
        question_id = _required_string(record, "question_id", index=index)
        gold_answer = _required_string(record, "answer", index=index)
        category = str(record.get("category", "unknown")).strip() or "unknown"
        category_totals[category] += 1

        output = generations.get(question_id)
        if output is None:
            error_counts["missing_generation"] += 1
            invalid_examples.append(
                {
                    "question_id": question_id,
                    "category": category,
                    "errors": ["missing generation"],
                    "gold_answer": gold_answer,
                    "output_excerpt": "",
                }
            )
            continue

        validation = validate_tiser_output(output, gold_answer)
        if validation["is_valid"]:
            traced_record = dict(record)
            traced_record["output"] = output.strip()
            filtered_records.append(traced_record)
            category_valid[category] += 1
            continue

        if validation["malformed_tags"]:
            error_counts["malformed_tags"] += 1

        for error in validation["errors"]:
            if error == "answer mismatch":
                error_counts["answer_mismatch"] += 1
            elif error.startswith("missing or empty <"):
                continue
            elif error == "answer could not be extracted":
                continue
            else:
                error_counts[error] += 1

        invalid_examples.append(
            {
                "question_id": question_id,
                "category": category,
                "errors": validation["errors"],
                "gold_answer": gold_answer,
                "extracted_answer": validation["extracted_answer"],
                "output_excerpt": output.strip()[:500],
            }
        )

    category_retention = {}
    for category in sorted(category_totals):
        total = category_totals[category]
        valid = category_valid[category]
        category_retention[category] = {
            "total": total,
            "valid": valid,
            "invalid": total - valid,
            "retention_rate": round(valid / total, 6) if total else 0.0,
        }

    summary = {
        "total_records": len(base_records),
        "valid_traces": len(filtered_records),
        "invalid_traces": len(base_records) - len(filtered_records),
        "answer_mismatch_count": error_counts["answer_mismatch"],
        "malformed_tag_count": error_counts["malformed_tags"],
        "missing_generation_count": error_counts["missing_generation"],
        "other_error_counts": {
            key: value
            for key, value in sorted(error_counts.items())
            if key not in {"answer_mismatch", "malformed_tags", "missing_generation"}
        },
        "category_wise_retention": category_retention,
        "invalid_examples": invalid_examples[:25],
    }
    return filtered_records, summary


def build_report(summary: dict[str, Any], load_errors: list[dict[str, Any]]) -> str:
    lines = [
        "# Tennis Trace Validation Report",
        "",
        "## Summary",
        "",
        f"- Total records: {summary['total_records']}",
        f"- Valid traces: {summary['valid_traces']}",
        f"- Invalid traces: {summary['invalid_traces']}",
        f"- Answer mismatch count: {summary['answer_mismatch_count']}",
        f"- Malformed tag count: {summary['malformed_tag_count']}",
        f"- Missing generation count: {summary['missing_generation_count']}",
        f"- Generation load errors: {len(load_errors)}",
        "",
        "## Category-Wise Retention",
        "",
        "| Category | Total | Valid | Invalid | Retention |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for category, stats in summary["category_wise_retention"].items():
        lines.append(
            f"| `{category}` | {stats['total']} | {stats['valid']} | "
            f"{stats['invalid']} | {stats['retention_rate']:.2%} |"
        )

    lines.extend(["", "## Invalid Output Examples", ""])
    if not summary["invalid_examples"]:
        lines.append("No invalid generated outputs were found.")
    else:
        for example in summary["invalid_examples"][:10]:
            lines.extend(
                [
                    f"### {example['question_id']}",
                    "",
                    f"- Category: `{example['category']}`",
                    f"- Gold answer: `{example['gold_answer']}`",
                    f"- Extracted answer: `{example.get('extracted_answer', '')}`",
                    f"- Errors: {', '.join(example['errors'])}",
                    "",
                    "```text",
                    example["output_excerpt"],
                    "```",
                    "",
                ]
            )

    if load_errors:
        lines.extend(["## Generation Load Errors", ""])
        for error in load_errors[:10]:
            lines.append(f"- `{error.get('line_number', '?')}`: {', '.join(error['errors'])}")
        lines.append("")

    return "\n".join(lines)


def run_prepare(args: argparse.Namespace) -> None:
    records = load_json_array(args.input)
    rows = build_request_rows(records)
    write_jsonl(args.output, rows)
    print(f"Loaded base records: {len(records)}")
    print(f"Wrote generation requests: {args.output}")


def run_validate(args: argparse.Namespace) -> None:
    base_records = load_json_array(args.base_records)
    generations, load_errors = load_generation_rows(args.input_generations)
    filtered_records, summary = validate_generations(base_records, generations)
    summary.update(
        {
            "base_records_path": str(Path(args.base_records)),
            "input_generations_path": str(Path(args.input_generations)),
            "output_path": str(Path(args.output)),
            "report_path": str(Path(args.report)),
            "summary_path": str(Path(args.summary)),
            "generation_load_errors": load_errors[:100],
        }
    )

    write_json(args.output, filtered_records)
    write_json(args.summary, summary)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(summary, load_errors), encoding="utf-8")

    print(f"Loaded base records: {summary['total_records']}")
    print(f"Loaded generation rows: {len(generations)}")
    print(f"Valid traces: {summary['valid_traces']}")
    print(f"Invalid traces: {summary['invalid_traces']}")
    print(f"Wrote filtered training set: {args.output}")
    print(f"Wrote validation report: {args.report}")
    print(f"Wrote validation summary: {args.summary}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and validate tennis TISER trace-generation artifacts."
    )
    parser.add_argument("--mode", choices=("prepare", "validate"), default="prepare")
    parser.add_argument("--input", help="Base tennis JSON array for prepare mode.")
    parser.add_argument("--output", required=True, help="Output path.")
    parser.add_argument(
        "--input-generations",
        help="JSONL generations with question_id and output for validate mode.",
    )
    parser.add_argument(
        "--base-records",
        help="Base tennis JSON array used to look up gold answers for validate mode.",
    )
    parser.add_argument("--report", help="Markdown validation report path.")
    parser.add_argument("--summary", help="JSON validation summary path.")
    args = parser.parse_args()

    if args.mode == "prepare" and not args.input:
        parser.error("--input is required in prepare mode")
    if args.mode == "validate":
        missing = [
            flag
            for flag, value in (
                ("--input-generations", args.input_generations),
                ("--base-records", args.base_records),
                ("--report", args.report),
                ("--summary", args.summary),
            )
            if not value
        ]
        if missing:
            parser.error(f"{', '.join(missing)} required in validate mode")
    return args


def main() -> None:
    args = parse_args()
    if args.mode == "prepare":
        run_prepare(args)
    else:
        run_validate(args)


if __name__ == "__main__":
    main()
