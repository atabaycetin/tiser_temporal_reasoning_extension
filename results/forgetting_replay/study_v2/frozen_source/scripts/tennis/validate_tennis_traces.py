"""Validate tennis TISER-style traced training data."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.tennis.normalize import normalize_tennis_answer_for_category
from src.tennis.trace_generation import extract_answer_from_output


DEFAULT_INPUT = Path("data/tennis/tennis_train_traced.json")
DEFAULT_FAILED_OUTPUT = Path(
    "results/tennis_domain_adaptation/trace_validation/failed_examples.json"
)
REQUIRED_FIELDS = ("dataset_name", "question_id", "question", "answer", "prompt", "output")
PLACEHOLDER_MARKERS = (
    "a detailed generated timeline will be added in the trace-generation step",
    "the final answer is checked against the provided gold answer",
    "the question asks for a temporal relation in the given tennis context",
)


def resolve_repo_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return REPO_ROOT / value


def load_records(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not path.exists():
        return [], [{"error_type": "missing_file", "message": f"file does not exist: {path}"}]

    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return [], [{"error_type": "empty_file", "message": "file is empty"}]

    if text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            return [], [json_error("invalid_json", error)]
        if not isinstance(data, list):
            return [], [
                {
                    "error_type": "invalid_json",
                    "message": f"expected a JSON array, got {type(data).__name__}",
                }
            ]
        raw_rows = data
    else:
        raw_rows = []
        load_errors = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw_rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                item = json_error("invalid_jsonl", error)
                item["line_number"] = line_number
                load_errors.append(item)
        if load_errors:
            return [], load_errors

    records: list[dict[str, Any]] = []
    row_errors = []
    for index, row in enumerate(raw_rows, start=1):
        if isinstance(row, dict):
            records.append(row)
        else:
            row_errors.append(
                {
                    "index": index,
                    "error_type": "invalid_record",
                    "errors": [f"record is not an object: {type(row).__name__}"],
                }
            )
    return records, row_errors


def json_error(error_type: str, error: json.JSONDecodeError) -> dict[str, Any]:
    return {
        "error_type": error_type,
        "message": error.msg,
        "line": error.lineno,
        "column": error.colno,
    }


def validate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()

    for index, record in enumerate(records, start=1):
        category = normalized_category(record)
        category_counts[category] += 1
        row_errors: list[str] = []

        for field in REQUIRED_FIELDS:
            if not non_empty_string(record.get(field)):
                row_errors.append(f"missing non-empty {field}")

        output = record.get("output")
        output_text = output if isinstance(output, str) else ""
        if output_text:
            if not has_tag(output_text, "reasoning"):
                row_errors.append("missing <reasoning>")
            if not has_tag(output_text, "answer"):
                row_errors.append("missing <answer>")
            if contains_placeholder(output_text):
                row_errors.append("placeholder trace")

        gold = record.get("answer")
        extracted_answer = extract_answer_from_output(output_text)
        if non_empty_string(gold) and has_tag(output_text, "answer"):
            normalized_gold = normalize_tennis_answer_for_category(
                str(gold),
                category=record.get("category"),
                tags=record.get("tags") if isinstance(record.get("tags"), list) else None,
            )
            normalized_pred = normalize_tennis_answer_for_category(
                extracted_answer,
                category=record.get("category"),
                tags=record.get("tags") if isinstance(record.get("tags"), list) else None,
            )
            if normalized_pred != normalized_gold:
                row_errors.append("answer mismatch")

        if row_errors:
            for error in row_errors:
                error_counts[error] += 1
            failures.append(
                {
                    "index": index,
                    "question_id": str(record.get("question_id", index)),
                    "category": category,
                    "errors": row_errors,
                    "gold_answer": record.get("answer", ""),
                    "extracted_answer": extracted_answer,
                    "output_excerpt": output_text.strip()[:500],
                }
            )

    return {
        "total_records": len(records),
        "valid_records": len(records) - len(failures),
        "invalid_records": len(failures),
        "category_counts": dict(sorted(category_counts.items())),
        "error_counts": dict(sorted(error_counts.items())),
        "failed_examples": failures,
    }


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def has_tag(text: str, tag: str) -> bool:
    pattern = rf"<{tag}>\s*.+?\s*</{tag}>"
    return re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE) is not None


def contains_placeholder(output: str) -> bool:
    lowered = output.casefold()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def normalized_category(record: dict[str, Any]) -> str:
    value = record.get("category", "unknown")
    if value is None:
        return "unknown"
    category = str(value).strip()
    return category or "unknown"


def write_failed_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "total_records": summary["total_records"],
        "valid_records": summary["valid_records"],
        "invalid_records": summary["invalid_records"],
        "category_counts": summary["category_counts"],
        "error_counts": summary["error_counts"],
        "failed_examples": summary["failed_examples"],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def print_summary(input_path: Path, failed_output_path: Path, summary: dict[str, Any]) -> None:
    print(f"Input: {relative_or_absolute(input_path)}")
    print(f"Total records: {summary['total_records']}")
    print(f"Valid records: {summary['valid_records']}")
    print(f"Invalid records: {summary['invalid_records']}")
    print("Counts by category:")
    for category, count in summary["category_counts"].items():
        print(f"  {category}: {count}")
    if summary["error_counts"]:
        print("Validation errors:")
        for error, count in summary["error_counts"].items():
            print(f"  {error}: {count}")
    print(f"Failed examples report: {relative_or_absolute(failed_output_path)}")


def relative_or_absolute(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate tennis traced training data.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="JSON array or JSONL trace file.")
    parser.add_argument(
        "--failed-output",
        default=str(DEFAULT_FAILED_OUTPUT),
        help="JSON report path for failed examples.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = resolve_repo_path(args.input)
    failed_output_path = resolve_repo_path(args.failed_output)

    records, load_errors = load_records(input_path)
    if load_errors:
        summary = {
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": len(load_errors),
            "category_counts": {},
            "error_counts": {"load_error": len(load_errors)},
            "failed_examples": load_errors,
        }
        write_failed_report(failed_output_path, summary)
        print_summary(input_path, failed_output_path, summary)
        raise SystemExit(1)

    summary = validate_records(records)
    write_failed_report(failed_output_path, summary)
    print_summary(input_path, failed_output_path, summary)
    raise SystemExit(0 if summary["invalid_records"] == 0 else 1)


if __name__ == "__main__":
    main()
