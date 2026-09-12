"""Build TISER-compatible records from audited tennis temporal QA examples."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from .prompts import build_standard_prompt, build_tennis_prompt
from .schema import validate_audited_record, validate_tiser_record


DEFAULT_SOURCE = "unknown"


def normalize_answer(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def extract_answer(output: str) -> str | None:
    match = re.search(r"<answer>\s*(.*?)\s*</answer>", output, flags=re.DOTALL)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def build_deterministic_output(gold_answer: str) -> str:
    return "\n".join(
        [
            "<reasoning>",
            "The question asks for a temporal relation in the given tennis context. The answer must be derived from the explicit order or timing of the events in the context.",
            "</reasoning>",
            "<timeline>",
            "The relevant events are stated in the context. A detailed generated timeline will be added in the trace-generation step.",
            "</timeline>",
            "<reflection>",
            "The final answer is checked against the provided gold answer and the explicit temporal context.",
            "</reflection>",
            f"<answer>{gold_answer}</answer>",
        ]
    )


def load_audited_examples(path: Path | str) -> list[dict[str, Any]]:
    input_path = Path(path)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {input_path}")

    examples: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Record {index} is not a JSON object")
        examples.append(item)
    return examples


def _clean_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [tag.strip() for tag in value if isinstance(tag, str) and tag.strip()]


def _get_source(example: dict[str, Any]) -> str:
    source = example.get("source")
    if isinstance(source, str) and source.strip():
        return source.strip()
    return DEFAULT_SOURCE


def build_prompt_record(
    example: dict[str, Any],
    *,
    dataset_name: str,
    prompt_builder: Callable[[str, str], str],
    include_output: bool = False,
) -> dict[str, Any]:
    context = str(example["context"]).strip()
    question = str(example["question"]).strip()
    answer = str(example["answer"]).strip()

    record: dict[str, Any] = {
        "dataset_name": dataset_name,
        "question_id": str(example["question_id"]).strip(),
        "question": question,
        "answer": answer,
        "prompt": prompt_builder(context, question),
        "category": str(example["category"]).strip(),
        "tags": _clean_tags(example.get("tags")),
        "source": _get_source(example),
    }

    if include_output:
        record["output"] = build_deterministic_output(answer)

    return record


def validate_converted_record(record: dict[str, Any], *, require_output: bool) -> list[str]:
    errors = validate_tiser_record(record, require_output=require_output)

    if require_output:
        output = record.get("output")
        if not isinstance(output, str):
            errors.append("output is not a string")
        else:
            extracted = extract_answer(output)
            if extracted is None:
                errors.append("output is missing <answer>...</answer>")
            elif normalize_answer(extracted) != normalize_answer(str(record.get("answer", ""))):
                errors.append("output answer does not match gold answer")

    return errors


def convert_examples(
    examples: list[dict[str, Any]],
    *,
    dataset_name: str,
    deterministic_output: bool = False,
    tiser_prompt_builder: Callable[[str, str], str] = build_tennis_prompt,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    tiser_records: list[dict[str, Any]] = []
    standard_records: list[dict[str, Any]] = []
    validation_errors: list[dict[str, Any]] = []
    source_defaulted = 0

    for index, example in enumerate(examples, start=1):
        audited_errors = validate_audited_record(example, allow_missing_source=True)
        if "source" not in example or not isinstance(example.get("source"), str) or not example.get("source", "").strip():
            source_defaulted += 1

        if audited_errors:
            validation_errors.append(
                {
                    "index": index,
                    "question_id": example.get("question_id"),
                    "stage": "audited_input",
                    "errors": audited_errors,
                }
            )
            continue

        tiser_record = build_prompt_record(
            example,
            dataset_name=dataset_name,
            prompt_builder=tiser_prompt_builder,
            include_output=deterministic_output,
        )
        standard_record = build_prompt_record(
            example,
            dataset_name=dataset_name,
            prompt_builder=build_standard_prompt,
            include_output=False,
        )

        tiser_errors = validate_converted_record(
            tiser_record, require_output=deterministic_output
        )
        standard_errors = validate_converted_record(standard_record, require_output=False)
        if tiser_errors:
            validation_errors.append(
                {
                    "index": index,
                    "question_id": example.get("question_id"),
                    "stage": "tiser_output",
                    "errors": tiser_errors,
                }
            )
        if standard_errors:
            validation_errors.append(
                {
                    "index": index,
                    "question_id": example.get("question_id"),
                    "stage": "standard_output",
                    "errors": standard_errors,
                }
            )

        if not tiser_errors and not standard_errors:
            tiser_records.append(tiser_record)
            standard_records.append(standard_record)

    category_distribution = Counter(record["category"] for record in tiser_records)
    source_distribution = Counter(record["source"] for record in tiser_records)
    summary = {
        "input_count": len(examples),
        "converted_count": len(tiser_records),
        "standard_prompt_count": len(standard_records),
        "deterministic_output": deterministic_output,
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors[:100],
        "source_defaulted_count": source_defaulted,
        "category_distribution": dict(sorted(category_distribution.items())),
        "source_distribution": dict(sorted(source_distribution.items())),
        "all_outputs_have_matching_answer": all(
            not validate_converted_record(record, require_output=deterministic_output)
            for record in tiser_records
        ),
    }
    return tiser_records, standard_records, summary


def write_json(path: Path | str, data: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
