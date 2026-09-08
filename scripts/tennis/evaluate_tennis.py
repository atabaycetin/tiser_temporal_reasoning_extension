"""Evaluate base models or LoRA adapters on the tennis temporal QA test set."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.experiment.artifacts import append, now
from src.experiment.evaluation import EvaluationStore, apply_tennis_view, evaluation_spec, write_predictions
from src.tennis.eval import extract_tennis_answer, render_markdown_report, score_prediction_rows
from src.tennis.normalize import tennis_exact_match_for_category, tennis_token_f1_for_category
from src.tennis.prompts import (
    build_standard_prompt,
    build_tennis_prompt,
    ensure_tiser_format_instruction,
)
from src.utils.config import load_config
from src.utils.io import git_sha
from src.utils.seeding import set_seed


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    cfg = load_config(str(resolve_repo_path(args.config)))
    apply_eval_overrides(cfg, args)

    test_file = resolve_repo_path(args.test_file or cfg.paths.test_file)
    output_dir = resolve_repo_path(args.output_dir)
    adapter_dir = None if args.no_adapter else resolve_adapter_dir(cfg, args.adapter_dir)

    if args.no_adapter and args.adapter_dir:
        raise ValueError("--adapter-dir cannot be used with --no-adapter")

    set_seed(cfg.seed)
    rows = load_records(test_file)
    limit = args.limit
    if limit is None:
        limit = cfg.eval.get("max_samples_per_split")
    if limit is not None:
        rows = rows[: int(limit)]
    if not rows:
        raise ValueError(f"No evaluation records found in {test_file}")

    prompts = [prompt_for_row(row, args.prompt_style) for row in rows]
    spec = evaluation_spec(rows, prompts, cfg, adapter_dir, input_file=test_file, view=args.scoring_view)
    spec.update({"condition": args.condition, "prompt_style": args.prompt_style})
    store = EvaluationStore(output_dir, spec, resume=args.resume, manifest=args.manifest)
    append(output_dir / "execution_attempts.jsonl", {"started_at": now(), "resume": bool(args.resume),
                                                      "completed_before_attempt": len(store.rows)})
    if len(store.rows) < len(rows):
        from src.inference.generate import generate_batch
        from src.model.loader import load_adapter_for_inference, load_base_for_inference
        model, tokenizer = (load_base_for_inference(cfg) if args.no_adapter else load_adapter_for_inference(cfg, str(adapter_dir)))
        checkpoint_rows = int(cfg.eval.get("checkpoint_rows", 64))
        if checkpoint_rows < cfg.eval.batch_size:
            raise ValueError("Evaluation checkpoint_rows must be at least batch_size")
        pending = []
        for start in range(len(store.rows), len(rows), cfg.eval.batch_size):
            part = rows[start:start + cfg.eval.batch_size]
            part_prompts = prompts[start:start + len(part)]
            generations = generate_batch(model, tokenizer, part_prompts, cfg.eval)
            pending.extend(build_prediction_rows(rows=part, prompts=part_prompts, generations=generations,
                                                 condition=args.condition, prompt_style=args.prompt_style))
            if len(pending) >= checkpoint_rows or start + len(part) == len(rows):
                store.add(pending)
                pending = []
    predictions = store.finish()
    metrics = score_prediction_rows(predictions)
    metrics.update(
        {
            "condition": args.condition,
            "prompt_style": args.prompt_style,
            "model_name": cfg.model.name,
            "adapter_dir": None if args.no_adapter else str(adapter_dir),
            "no_adapter": bool(args.no_adapter),
            "test_file": str(test_file),
            "limit": limit,
            "batch_size": cfg.eval.batch_size,
            "max_new_tokens": cfg.eval.max_new_tokens,
        }
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "predictions.jsonl"
    metrics_path = output_dir / "metrics.json"
    report_path = output_dir / "metrics_report.md"
    run_meta_path = output_dir / "run_meta.json"

    write_json(metrics_path, metrics)
    if args.scoring_view:
        primary = apply_tennis_view(predictions, args.scoring_view, test_file)
        write_predictions(output_dir / "primary_predictions.jsonl", primary)
        write_json(output_dir / "primary_metrics.json", score_prediction_rows(primary))
    write_text(report_path, render_markdown_report(metrics, predictions_path))
    if not run_meta_path.exists():
        write_json(
            run_meta_path,
            build_run_meta(
                cfg=cfg,
                args=args,
                test_file=test_file,
                output_dir=output_dir,
                adapter_dir=adapter_dir,
                n_records=len(rows),
            ),
        )
    append(output_dir / "execution_attempts.jsonl", {"completed_at": now(), "status": "complete",
                                                      "completed_records": len(predictions)})

    overall = metrics["overall"]
    print(
        "[tennis-eval] {condition}: EM={em:.4f} F1={f1:.4f} malformed={bad}/{n}".format(
            condition=args.condition,
            em=overall["em"],
            f1=overall["f1"],
            bad=overall["malformed_count"],
            n=overall["n"],
        )
    )
    print(f"[tennis-eval] wrote artifacts to {output_dir}")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a base Qwen model or PEFT adapter on tennis temporal QA."
    )
    parser.add_argument("--config", required=True, help="Tennis evaluation config YAML.")
    parser.add_argument("--test-file", default=None, help="Tennis test JSON/JSONL file.")
    parser.add_argument("--adapter-dir", default=None, help="PEFT adapter directory.")
    parser.add_argument("--condition", required=True, help="Condition label, e.g. base_qwen.")
    parser.add_argument("--output-dir", required=True, help="Directory for scored artifacts.")
    parser.add_argument("--no-adapter", action="store_true", help="Evaluate base model only.")
    parser.add_argument("--limit", type=int, default=None, help="Limit examples for smoke tests.")
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--manifest", help="Require this exact evaluation_spec.json")
    parser.add_argument("--scoring-view", help="Frozen audit eligibility/gold sidecar")
    parser.add_argument(
        "--prompt-style",
        choices=("tiser", "standard"),
        default="tiser",
        help="Use TISER trace prompt or direct-answer standard prompt.",
    )
    return parser.parse_args(argv)


def apply_eval_overrides(cfg: Any, args: argparse.Namespace) -> None:
    if args.max_new_tokens is not None:
        cfg.eval.max_new_tokens = args.max_new_tokens
    if args.batch_size is not None:
        cfg.eval.batch_size = args.batch_size


def resolve_repo_path(path: str | os.PathLike[str]) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return REPO_ROOT / value


def resolve_adapter_dir(cfg: Any, adapter_dir: str | None) -> Path:
    if adapter_dir:
        return resolve_repo_path(adapter_dir)
    return Path(cfg.paths.model_dir) / cfg.run_name / "adapter"


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    if text.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError(f"Expected a JSON array in {path}")
        return require_object_rows(data, path)

    rows = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"Line {line_number} of {path} is not a JSON object")
        rows.append(row)
    return rows


def require_object_rows(data: list[Any], path: Path) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Record {index} of {path} is not a JSON object")
        rows.append(row)
    return rows


def prompt_for_row(row: dict[str, Any], prompt_style: str) -> str:
    if prompt_style == "tiser":
        prompt = row.get("prompt")
        if isinstance(prompt, str) and prompt.strip():
            return ensure_tiser_format_instruction(prompt)
        context = row.get("context")
        question = row.get("question")
        if isinstance(context, str) and isinstance(question, str):
            return build_tennis_prompt(context, question)
        raise ValueError(f"Record {row.get('question_id')} has no usable TISER prompt")

    standard_prompt = row.get("standard_prompt")
    if isinstance(standard_prompt, str) and standard_prompt.strip():
        return standard_prompt
    context = row.get("context")
    question = row.get("question")
    if isinstance(context, str) and isinstance(question, str):
        return build_standard_prompt(context, question)
    extracted_context, extracted_question = extract_context_question(row.get("prompt", ""))
    if extracted_context and extracted_question:
        return build_standard_prompt(extracted_context, extracted_question)
    raise ValueError(f"Record {row.get('question_id')} cannot be converted to standard prompt")


def extract_context_question(prompt: Any) -> tuple[str | None, str | None]:
    if not isinstance(prompt, str):
        return None, None
    context_marker = "Temporal context:"
    question_marker = "\n\nQuestion:"
    answer_marker = "\n\nReturn"
    if context_marker not in prompt or question_marker not in prompt:
        return None, None
    context_start = prompt.index(context_marker) + len(context_marker)
    question_start = prompt.index(question_marker)
    question_text_start = question_start + len(question_marker)
    question_end = prompt.find(answer_marker, question_text_start)
    if question_end == -1:
        question_end = len(prompt)
    return prompt[context_start:question_start].strip(), prompt[question_text_start:question_end].strip()


def build_prediction_rows(
    *,
    rows: list[dict[str, Any]],
    prompts: list[str],
    generations: list[str],
    condition: str,
    prompt_style: str,
) -> list[dict[str, Any]]:
    if not (len(rows) == len(prompts) == len(generations)):
        raise ValueError("Generation/prompt/input counts differ")
    predictions = []
    for index, (row, prompt, raw_generation) in enumerate(
        zip(rows, prompts, generations), start=1
    ):
        gold = str(row.get("answer") or row.get("gold") or "")
        category = str(row.get("category") or "unknown")
        tags = row.get("tags") if isinstance(row.get("tags"), list) else []
        pred_answer, malformed = extract_prediction(
            raw_generation,
            prompt_style,
            category=category,
            tags=tags,
            gold=gold,
        )
        predictions.append(
            {
                "question_id": str(row.get("question_id") or index),
                "dataset_name": str(row.get("dataset_name") or "tennis_temporal"),
                "category": category,
                "tags": tags,
                "prompt": prompt,
                "gold": gold,
                "raw_generation": raw_generation,
                "pred_answer": pred_answer,
                "malformed": malformed,
                "em": tennis_exact_match_for_category(
                    pred_answer,
                    gold,
                    category=category,
                    tags=tags,
                ),
                "f1": tennis_token_f1_for_category(
                    pred_answer,
                    gold,
                    category=category,
                    tags=tags,
                ),
                "condition": condition,
            }
        )
    return predictions


def extract_prediction(
    raw_generation: str,
    prompt_style: str,
    *,
    category: str | None = None,
    tags: list[str] | None = None,
    gold: str | None = None,
) -> tuple[str, bool]:
    answer, malformed = extract_tennis_answer(
        raw_generation,
        category=category,
        tags=tags,
        gold=gold,
    )
    if prompt_style == "tiser" or answer:
        return answer, malformed

    direct = raw_generation.strip()
    if not direct:
        return "", True
    first_line = next((line.strip() for line in direct.splitlines() if line.strip()), "")
    return first_line, False


def build_run_meta(
    *,
    cfg: Any,
    args: argparse.Namespace,
    test_file: Path,
    output_dir: Path,
    adapter_dir: Path | None,
    n_records: int,
) -> dict[str, Any]:
    return {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "command": [Path(sys.argv[0]).as_posix(), *sys.argv[1:]],
        "condition": args.condition,
        "prompt_style": args.prompt_style,
        "test_file": str(test_file),
        "output_dir": str(output_dir),
        "adapter_dir": None if adapter_dir is None else str(adapter_dir),
        "no_adapter": bool(args.no_adapter),
        "n_records": n_records,
        "limit": args.limit,
        "model_name": cfg.model.name,
        "decoding": {
            "batch_size": cfg.eval.batch_size,
            "max_new_tokens": cfg.eval.max_new_tokens,
            "do_sample": cfg.eval.do_sample,
        },
        "library_versions": library_versions(),
        "config": cfg,
    }


def library_versions() -> dict[str, str]:
    versions = {}
    for package in ("torch", "transformers", "peft", "accelerate", "bitsandbytes"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
