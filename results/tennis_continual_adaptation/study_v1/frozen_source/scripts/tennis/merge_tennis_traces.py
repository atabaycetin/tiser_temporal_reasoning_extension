"""Merge externally generated tennis TISER traces into training records."""

from __future__ import annotations

import argparse
import copy
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


DEFAULT_SOURCE = Path("data/tennis/tennis_train.json")
DEFAULT_GENERATED = Path(
    "results/tennis_domain_adaptation/trace_generation/generated_traces_50.jsonl"
)
DEFAULT_OUTPUT = Path("data/tennis/tennis_train_traced_50.json")
DEFAULT_FAILED_OUTPUT = Path(
    "results/tennis_domain_adaptation/trace_generation/merge_failed_50.json"
)
REQUIRED_TRACE_TAGS = ("reasoning", "timeline", "reflection", "answer")
PLACEHOLDER_MARKERS = (
    "a detailed generated timeline will be added in the trace-generation step",
    "the final answer is checked against the provided gold answer",
    "the question asks for a temporal relation in the given tennis context",
    "gold_answer_exactly",
    "<timeline>...</timeline>",
    "<reflection>...</reflection>",
    "<answer>...</answer>",
)


def resolve_repo_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return REPO_ROOT / value


def load_json_array(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array")

    records: list[dict[str, Any]] = []
    for index, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: record {index} is not an object")
        records.append(row)
    return records


def load_generated_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                failures.append(
                    {
                        "line_number": line_number,
                        "question_id": "",
                        "errors": [f"invalid JSONL: {error.msg}"],
                    }
                )
                continue
            if not isinstance(row, dict):
                failures.append(
                    {
                        "line_number": line_number,
                        "question_id": "",
                        "errors": [f"generated record is not an object: {type(row).__name__}"],
                    }
                )
                continue
            records.append(row)

    return records, failures


def source_by_question_id(
    source_records: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    source_index: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    seen: set[str] = set()

    for index, record in enumerate(source_records, start=1):
        question_id = clean_question_id(record.get("question_id"))
        if not question_id:
            failures.append(
                {
                    "source_index": index,
                    "question_id": "",
                    "errors": ["source record is missing question_id"],
                }
            )
            continue
        if question_id in seen:
            failures.append(
                {
                    "source_index": index,
                    "question_id": question_id,
                    "errors": ["duplicate source question_id"],
                }
            )
            continue
        seen.add(question_id)
        source_index[question_id] = record

    return source_index, failures


def clean_question_id(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def validate_generated_trace(
    generated_record: dict[str, Any],
    source_record: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any]]:
    question_id = clean_question_id(generated_record.get("question_id"))
    output = generated_record.get("output")
    output_text = output if isinstance(output, str) else ""
    errors: list[str] = []

    if not question_id:
        errors.append("missing generated question_id")
    if source_record is None:
        errors.append("question_id does not exist in source")
    if not isinstance(output, str) or not output.strip():
        errors.append("missing generated output")

    for tag in REQUIRED_TRACE_TAGS:
        if output_text and not has_non_empty_tag(output_text, tag):
            errors.append(f"missing <{tag}>")

    if output_text and contains_placeholder(output_text):
        errors.append("placeholder trace")

    extracted_answer = extract_answer_from_output(output_text)
    normalized_gold = ""
    normalized_extracted = ""
    if source_record is not None:
        gold_answer = source_record.get("answer")
        if not isinstance(gold_answer, str) or not gold_answer.strip():
            errors.append("source record is missing gold answer")
        else:
            tags = source_record.get("tags")
            normalized_gold = normalize_tennis_answer_for_category(
                gold_answer,
                category=source_record.get("category"),
                tags=tags if isinstance(tags, list) else None,
            )
            normalized_extracted = normalize_tennis_answer_for_category(
                extracted_answer,
                category=source_record.get("category"),
                tags=tags if isinstance(tags, list) else None,
            )
            if has_non_empty_tag(output_text, "answer") and normalized_extracted != normalized_gold:
                errors.append("answer mismatch")

    failure = {
        "question_id": question_id or str(generated_record.get("question_id", "")),
        "errors": errors,
        "gold_answer": "" if source_record is None else source_record.get("answer", ""),
        "extracted_answer": extracted_answer,
        "normalized_gold_answer": normalized_gold,
        "normalized_extracted_answer": normalized_extracted,
        "output_excerpt": output_text.strip()[:500],
    }
    return not errors, failure


def has_non_empty_tag(text: str, tag: str) -> bool:
    pattern = rf"<{tag}>\s*.+?\s*</{tag}>"
    return re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE) is not None


def contains_placeholder(output: str) -> bool:
    lowered = output.casefold()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def merge_records(
    source_records: list[dict[str, Any]],
    generated_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    source_index, source_failures = source_by_question_id(source_records)
    merged_records: list[dict[str, Any]] = []
    failed_records: list[dict[str, Any]] = list(source_failures)
    seen_generated: set[str] = set()
    error_counts: Counter[str] = Counter()

    for failure in source_failures:
        error_counts.update(failure["errors"])

    for line_index, generated_record in enumerate(generated_records, start=1):
        question_id = clean_question_id(generated_record.get("question_id"))
        source_record = source_index.get(question_id)
        is_valid, failure = validate_generated_trace(generated_record, source_record)
        failure["generated_index"] = line_index

        if question_id:
            if question_id in seen_generated:
                is_valid = False
                failure["errors"].append("duplicate generated question_id")
            seen_generated.add(question_id)

        if is_valid and source_record is not None:
            merged_record = copy.deepcopy(source_record)
            merged_record["output"] = generated_record["output"]
            merged_records.append(merged_record)
        else:
            failed_records.append(failure)
            error_counts.update(failure["errors"])

    summary = {
        "source_records": len(source_records),
        "generated_records": len(generated_records),
        "merged_records": len(merged_records),
        "failed_records": len(failed_records),
        "error_counts": dict(sorted(error_counts.items())),
    }
    return merged_records, failed_records, summary


def write_json_array(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_failed_report(path: Path, failures: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **summary,
        "failed_examples": failures,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def relative_or_absolute(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge valid generated tennis TISER traces into train records."
    )
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Source tennis train JSON.")
    parser.add_argument("--generated", default=str(DEFAULT_GENERATED), help="Generated traces JSONL.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Merged valid JSON output.")
    parser.add_argument(
        "--failed-output",
        default=str(DEFAULT_FAILED_OUTPUT),
        help="JSON report for invalid or failed generated traces.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = resolve_repo_path(args.source)
    generated_path = resolve_repo_path(args.generated)
    output_path = resolve_repo_path(args.output)
    failed_output_path = resolve_repo_path(args.failed_output)

    source_records = load_json_array(source_path)
    generated_records, load_failures = load_generated_jsonl(generated_path)
    merged_records, failed_records, summary = merge_records(source_records, generated_records)

    if load_failures:
        failed_records = load_failures + failed_records
        summary["failed_records"] = len(failed_records)
        counts = Counter(summary["error_counts"])
        for failure in load_failures:
            counts.update(failure["errors"])
        summary["error_counts"] = dict(sorted(counts.items()))

    write_json_array(output_path, merged_records)
    write_failed_report(failed_output_path, failed_records, summary)

    print(f"Source: {relative_or_absolute(source_path)}")
    print(f"Generated: {relative_or_absolute(generated_path)}")
    print(f"Merged valid records: {summary['merged_records']}")
    print(f"Failed records: {summary['failed_records']}")
    print(f"Output: {relative_or_absolute(output_path)}")
    print(f"Failed report: {relative_or_absolute(failed_output_path)}")
    raise SystemExit(0 if summary["failed_records"] == 0 else 1)


if __name__ == "__main__":
    main()
