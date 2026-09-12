"""Train tennis-domain TISER adapters with data validation.

This is intentionally a thin wrapper around src.train.trainer.run_training.
It applies tennis-specific CLI overrides, validates the selected training file,
then hands control to the baseline training stack.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.tennis.trace_generation import extract_answer_from_output, normalize_answer
from src.utils.config import load_config


DEFAULT_TRACED_TRAIN = Path("data/tennis/tennis_train_traced.json")
FALLBACK_TRAIN = Path("data/tennis/tennis_train.json")
PLACEHOLDER_MARKERS = (
    "a detailed generated timeline will be added in the trace-generation step",
    "the final answer is checked against the provided gold answer",
    "the question asks for a temporal relation in the given tennis context",
)


def main() -> None:
    args = parse_args()
    cfg = load_config(str(resolve_repo_path(args.config)))

    if args.run_name is not None:
        cfg.run_name = args.run_name
    if args.subset is not None:
        cfg.train.subset_size = args.subset
    if args.epochs is not None:
        cfg.train.num_epochs = args.epochs
    if args.max_steps is not None:
        cfg.train.max_steps = args.max_steps
    if args.resume_from_checkpoint is not None:
        cfg.train.resume_from_checkpoint = str(resolve_repo_path(args.resume_from_checkpoint))

    train_file = select_train_file(args.train_file or cfg.paths.train_file)
    cfg.paths.train_file = str(train_file)
    base_adapter = args.base_adapter or cfg.model.get("base_adapter")
    if base_adapter is not None:
        cfg.model.base_adapter = str(
            validate_base_adapter(base_adapter, expected_base_model=cfg.model.name)
        )
    if args.test_file is not None:
        cfg.paths.test_file = str(resolve_repo_path(args.test_file))
    if args.output_dir is not None:
        cfg.paths.output_dir = str(run_base_dir(args.output_dir, cfg.run_name))
    if args.model_dir is not None:
        cfg.paths.model_dir = str(run_base_dir(args.model_dir, cfg.run_name))

    validation = validate_training_file(train_file, min_match_rate=args.min_answer_match_rate)
    print_validation_summary(train_file, validation)
    enforce_placeholder_policy(validation, allow_placeholder_traces=args.allow_placeholder_traces)
    print_resolved_outputs(cfg)

    from src.train.trainer import run_training

    run_training(cfg)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a tennis-domain adapter using the existing TISER trainer."
    )
    parser.add_argument("--config", default="config/config_tennis.yaml")
    parser.add_argument(
        "--train-file",
        default=None,
        help=(
            "Training JSON/JSONL. Defaults to the config path. If the requested "
            "tennis_train_traced.json is absent, data/tennis/tennis_train.json is used."
        ),
    )
    parser.add_argument("--test-file", default=None)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--model-dir", default=None)
    parser.add_argument(
        "--base-adapter",
        default=None,
        help=(
            "Existing PEFT/LoRA adapter to continue training from, e.g. "
            "checkpoints/adapter for the TISER-fine-tuned Qwen 7B adapter."
        ),
    )
    parser.add_argument("--subset", type=int, default=None, help="Cap training examples.")
    parser.add_argument("--epochs", type=float, default=None)
    parser.add_argument("--resume-from-checkpoint", help="Full trainer checkpoint, including optimizer/RNG/token counters")
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help=(
            "Cap optimizer steps. A positive value overrides epoch-derived length "
            "and is useful for compute-matched replay comparisons."
        ),
    )
    parser.add_argument(
        "--min-answer-match-rate",
        type=float,
        default=0.95,
        help="Abort if extracted <answer> matches gold for less than this fraction.",
    )
    parser.add_argument(
        "--allow-placeholder-traces",
        action="store_true",
        help=(
            "Allow training on placeholder-style traces. This is only suitable for "
            "plumbing/smoke checks and is not scientifically valid."
        ),
    )
    args = parser.parse_args()
    if args.max_steps is not None and args.max_steps < 1:
        parser.error("--max-steps must be at least 1")
    return args


def resolve_repo_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return REPO_ROOT / value


def run_base_dir(path: str | Path, run_name: str) -> Path:
    """Return the base dir expected by the baseline trainer.

    The trainer writes to paths.output_dir/run_name and paths.model_dir/run_name.
    If the user passes an explicit run directory whose basename already equals
    run_name, use its parent to avoid run_name/run_name duplication while
    preserving existing trainer behavior.
    """

    resolved = resolve_repo_path(path)
    if resolved.name == run_name:
        return resolved.parent
    return resolved


def select_train_file(requested_path: str | Path) -> Path:
    requested = resolve_repo_path(requested_path)
    if requested.exists():
        return requested

    default_traced = resolve_repo_path(DEFAULT_TRACED_TRAIN)
    fallback = resolve_repo_path(FALLBACK_TRAIN)
    if requested == default_traced and fallback.exists():
        print(
            "[tennis-train][warning] "
            f"{relative_or_absolute(default_traced)} is missing; falling back to "
            f"{relative_or_absolute(fallback)}."
        )
        print(
            "[tennis-train][warning] Fallback data may contain placeholder traces. "
            "Training results are not scientifically meaningful unless high-quality "
            "validated traces are available."
        )
        return fallback

    raise FileNotFoundError(f"Training file does not exist: {requested}")


def validate_base_adapter(path: str | Path, *, expected_base_model: str) -> Path:
    adapter_dir = resolve_repo_path(path)
    if not adapter_dir.is_dir():
        raise FileNotFoundError(f"Base adapter directory does not exist: {adapter_dir}")

    config_path = adapter_dir / "adapter_config.json"
    weights_path = adapter_dir / "adapter_model.safetensors"
    if not config_path.is_file():
        raise FileNotFoundError(f"Base adapter is missing adapter_config.json: {adapter_dir}")
    if not weights_path.is_file():
        raise FileNotFoundError(f"Base adapter is missing adapter_model.safetensors: {adapter_dir}")

    with config_path.open(encoding="utf-8") as f:
        adapter_config = json.load(f)
    actual_base = adapter_config.get("base_model_name_or_path")
    if actual_base != expected_base_model:
        raise ValueError(
            "Base adapter/model mismatch: "
            f"adapter was trained from {actual_base!r}, but config model.name is "
            f"{expected_base_model!r}."
        )
    return adapter_dir


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    if text.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError(f"{path}: expected a JSON array")
        rows = data
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]

    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: record {index} is not a JSON object")
        records.append(row)
    return records


def validate_training_file(path: Path, *, min_match_rate: float) -> dict[str, Any]:
    records = load_records(path)
    if not records:
        raise ValueError(f"{path}: no training records found")

    missing_prompt: list[str] = []
    missing_output: list[str] = []
    missing_answer_tag: list[str] = []
    missing_gold: list[str] = []
    mismatched_answer: list[dict[str, str]] = []
    placeholder_count = 0

    for index, record in enumerate(records, start=1):
        row_id = row_identifier(record, index)
        prompt = record.get("prompt")
        output = record.get("output")
        gold = record.get("answer", record.get("gold_answer", record.get("gold")))

        if not isinstance(prompt, str) or not prompt.strip():
            missing_prompt.append(row_id)
        if not isinstance(output, str) or not output.strip():
            missing_output.append(row_id)
            continue
        if "<answer>" not in output.casefold():
            missing_answer_tag.append(row_id)

        extracted = extract_answer_from_output(output)
        if gold is None or not str(gold).strip():
            missing_gold.append(row_id)
        elif normalize_answer(extracted) != normalize_answer(str(gold)):
            mismatched_answer.append(
                {
                    "id": row_id,
                    "gold": str(gold),
                    "extracted": extracted,
                }
            )

        lowered_output = output.casefold()
        if any(marker in lowered_output for marker in PLACEHOLDER_MARKERS):
            placeholder_count += 1

    fatal_errors = []
    if missing_prompt:
        fatal_errors.append(f"{len(missing_prompt)} records missing non-empty prompt")
    if missing_output:
        fatal_errors.append(f"{len(missing_output)} records missing non-empty output")
    if missing_answer_tag:
        fatal_errors.append(f"{len(missing_answer_tag)} records missing <answer>")
    if missing_gold:
        fatal_errors.append(f"{len(missing_gold)} records missing gold answer")

    checked_answers = len(records) - len(missing_output) - len(missing_gold)
    matched_answers = checked_answers - len(mismatched_answer)
    match_rate = matched_answers / checked_answers if checked_answers else 0.0
    if match_rate < min_match_rate:
        fatal_errors.append(
            "extracted <answer> matches gold for "
            f"{match_rate:.2%}, below required {min_match_rate:.2%}"
        )

    if fatal_errors:
        examples = {
            "missing_prompt": missing_prompt[:5],
            "missing_output": missing_output[:5],
            "missing_answer_tag": missing_answer_tag[:5],
            "missing_gold": missing_gold[:5],
            "mismatched_answer": mismatched_answer[:5],
        }
        raise ValueError(
            "Training data validation failed: "
            + "; ".join(fatal_errors)
            + f". Examples: {examples}"
        )

    return {
        "records": len(records),
        "checked_answers": checked_answers,
        "matched_answers": matched_answers,
        "answer_match_rate": match_rate,
        "placeholder_count": placeholder_count,
        "placeholder_rate": placeholder_count / len(records),
        "mismatched_answer_count": len(mismatched_answer),
    }


def row_identifier(record: dict[str, Any], index: int) -> str:
    value = record.get("question_id") or record.get("id") or index
    return str(value)


def print_validation_summary(path: Path, validation: dict[str, Any]) -> None:
    print(
        "[tennis-train] validated {path}: {records} records, answer match {rate:.2%}".format(
            path=relative_or_absolute(path),
            records=validation["records"],
            rate=validation["answer_match_rate"],
        )
    )
    if validation["placeholder_count"]:
        print(
            "[tennis-train][warning] detected placeholder-style traces in "
            f"{validation['placeholder_count']}/{validation['records']} records "
            f"({validation['placeholder_rate']:.2%})."
        )
    if validation["placeholder_rate"] >= 0.5:
        print(
            "[tennis-train][warning] Most training outputs look like placeholders. "
            "Use this only for plumbing/smoke checks; results are not scientifically "
            "meaningful until high-quality traces replace them."
        )


def enforce_placeholder_policy(
    validation: dict[str, Any], *, allow_placeholder_traces: bool
) -> None:
    if not validation["placeholder_count"]:
        return

    warning = (
        "Placeholder traces are not scientifically valid training targets. They "
        "can only verify trainer plumbing and must not be used for adapter-quality "
        "or transfer claims."
    )
    if allow_placeholder_traces:
        print(f"[tennis-train][warning] --allow-placeholder-traces set. {warning}")
        return

    raise ValueError(
        "[tennis-train] refusing to train on placeholder-style traces by default. "
        f"{warning} Regenerate validated traces at "
        "data/tennis/tennis_train_traced.json, or pass "
        "--allow-placeholder-traces for a plumbing-only smoke run."
    )


def print_resolved_outputs(cfg: Any) -> None:
    output_run_dir = Path(cfg.paths.output_dir) / cfg.run_name
    adapter_dir = Path(cfg.paths.model_dir) / cfg.run_name / "adapter"
    base_adapter = cfg.model.get("base_adapter")
    print(f"[tennis-train] run_name: {cfg.run_name}")
    print(f"[tennis-train] train_file: {relative_or_absolute(Path(cfg.paths.train_file))}")
    if base_adapter:
        print(f"[tennis-train] base_adapter: {relative_or_absolute(Path(base_adapter))}")
    print(f"[tennis-train] output_run_dir: {relative_or_absolute(output_run_dir)}")
    print(f"[tennis-train] adapter_dir: {relative_or_absolute(adapter_dir)}")


def relative_or_absolute(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
