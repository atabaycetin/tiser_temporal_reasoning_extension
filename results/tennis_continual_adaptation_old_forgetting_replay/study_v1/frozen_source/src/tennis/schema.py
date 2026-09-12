"""Schema definitions and validation helpers for tennis temporal QA records."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


RAW_KEYS = (
    "context",
    "question",
    "answer",
)

AUDITED_KEYS = (
    "context",
    "question",
    "answer",
    "question_id",
    "category",
    "tags",
    "source",
)

TISER_TRAIN_KEYS = (
    "dataset_name",
    "question_id",
    "question",
    "answer",
    "prompt",
    "output",
    "category",
    "tags",
    "source",
)

TISER_TEST_KEYS = (
    "dataset_name",
    "question_id",
    "question",
    "answer",
    "prompt",
    "category",
    "tags",
    "source",
)


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def missing_or_empty_string_errors(record: dict[str, Any], keys: Iterable[str]) -> list[str]:
    errors: list[str] = []
    for key in keys:
        if key not in record:
            errors.append(f"missing key: {key}")
        elif not is_non_empty_string(record[key]):
            errors.append(f"empty or non-string key: {key}")
    return errors


def validate_raw_record(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["record is not an object"]
    return missing_or_empty_string_errors(record, RAW_KEYS)


def validate_audited_record(record: Any, *, allow_missing_source: bool = False) -> list[str]:
    if not isinstance(record, dict):
        return ["record is not an object"]

    required = list(AUDITED_KEYS)
    if allow_missing_source:
        required.remove("source")

    string_required = [key for key in required if key != "tags"]
    errors = missing_or_empty_string_errors(record, string_required)
    tags = record.get("tags")
    if "tags" not in record:
        errors.append("missing key: tags")
    elif not isinstance(tags, list) or not all(is_non_empty_string(tag) for tag in tags):
        errors.append("tags must be a list of non-empty strings")
    return errors


def validate_tiser_record(record: Any, *, require_output: bool) -> list[str]:
    if not isinstance(record, dict):
        return ["record is not an object"]

    required = TISER_TRAIN_KEYS if require_output else TISER_TEST_KEYS
    string_required = [key for key in required if key != "tags"]
    errors = missing_or_empty_string_errors(record, string_required)
    tags = record.get("tags")
    if "tags" not in record:
        errors.append("missing key: tags")
    elif not isinstance(tags, list) or not all(is_non_empty_string(tag) for tag in tags):
        errors.append("tags must be a list of non-empty strings")
    return errors
