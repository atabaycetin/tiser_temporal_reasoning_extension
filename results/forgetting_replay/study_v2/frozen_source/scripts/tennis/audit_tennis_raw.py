"""Audit raw tennis temporal QA examples.

The script validates the minimal raw schema, assigns stable ids where needed,
adds rule-based category labels, flags duplicate-like examples, and writes both
an enriched dataset and audit summaries.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


CATEGORY_ORDER = [
    "yes_no_before_after",
    "which_first_last",
    "immediate_before_after",
    "duration_minutes",
    "overlap_while_during",
    "tournament_round_sequence",
    "tennis_injury_or_medical",
    "other_temporal",
]

REQUIRED_FIELDS = ("context", "question", "answer")
NEAR_DUPLICATE_RATIO = 0.92
NEAR_DUPLICATE_JACCARD = 0.88


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit raw tennis temporal QA data.")
    parser.add_argument("--input", default="data/tennis/raw/tennis_raw.json")
    parser.add_argument("--output", default="data/tennis/processed/tennis_raw_audited.json")
    parser.add_argument(
        "--report",
        default="results/tennis_domain_adaptation/raw_audit/tennis_raw_audit_report.md",
    )
    parser.add_argument(
        "--summary",
        default="results/tennis_domain_adaptation/raw_audit/tennis_raw_audit_summary.json",
    )
    return parser.parse_args()


def load_json_array(path: Path) -> list[Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Input is not valid JSON: {path} ({exc})") from exc

    if not isinstance(data, list):
        raise SystemExit(f"Input must be a JSON array: {path}")
    return data


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return normalize_whitespace(value).lower()


def answer_key(value: Any) -> str:
    if not isinstance(value, str):
        return "<non-string>"
    normalized = normalize_whitespace(value)
    return normalized if normalized else "<blank>"


def validate_record(record: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record is not a JSON object"]

    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing field: {field}")
            continue
        if not isinstance(record[field], str):
            errors.append(f"field is not a string: {field}")
            continue
        if not record[field].strip():
            errors.append(f"field is blank: {field}")
    return errors


def infer_categories(context: Any, question: Any) -> tuple[str, list[str]]:
    context_text = normalize_text(context)
    question_text = normalize_text(question)
    combined_text = f"{context_text} {question_text}"
    tags: list[str] = []

    if re.match(r"^(did|was|were)\b", question_text) and re.search(
        r"\b(before|after)\b", question_text
    ):
        tags.append("yes_no_before_after")

    which_first_last_phrases = (
        "which happened first",
        "which event happened last",
        "which happened last",
    )
    if any(phrase in question_text for phrase in which_first_last_phrases):
        tags.append("which_first_last")

    immediate_phrases = (
        "immediately before",
        "immediately after",
        "what happened before",
        "what happened after",
    )
    if any(phrase in question_text for phrase in immediate_phrases):
        tags.append("immediate_before_after")

    if (
        "how many minutes" in question_text
        or "how long" in question_text
        or re.search(r"\b[ap]\.m\.\b", question_text)
        or re.search(r"\bminutes?\b", question_text)
    ):
        tags.append("duration_minutes")

    if re.search(r"\b(while|during)\b", question_text) or "at the same time" in question_text:
        tags.append("overlap_while_during")

    round_terms = (
        "quarterfinal",
        "quarter-final",
        "semifinal",
        "semi-final",
        "final",
        "round of 16",
        "first round",
        "second round",
    )
    if any(term in question_text for term in round_terms):
        tags.append("tournament_round_sequence")

    medical_terms = (
        "trainer",
        "medical timeout",
        "treatment",
        "injury",
        "shoulder",
        "wrist",
        "ankle",
        "leg",
    )
    if any(term in combined_text for term in medical_terms):
        tags.append("tennis_injury_or_medical")

    if not tags:
        tags.append("other_temporal")

    for category in CATEGORY_ORDER:
        if category in tags:
            return category, tags
    return "other_temporal", tags


def token_set(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def length_stats(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
        }

    ordered = sorted(values)
    return {
        "count": len(values),
        "min": ordered[0],
        "max": ordered[-1],
        "mean": round(statistics.fmean(ordered), 2),
        "median": round(statistics.median(ordered), 2),
        "p25": ordered[int((len(ordered) - 1) * 0.25)],
        "p75": ordered[int((len(ordered) - 1) * 0.75)],
    }


def field_lengths(records: list[dict[str, Any]], field: str) -> dict[str, dict[str, float | int | None]]:
    chars: list[int] = []
    tokens: list[int] = []
    for record in records:
        value = record.get(field)
        if isinstance(value, str):
            chars.append(len(value))
            tokens.append(len(re.findall(r"\S+", value)))
    return {
        "characters": length_stats(chars),
        "tokens": length_stats(tokens),
    }


def find_duplicates(records: list[dict[str, Any]]) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    duplicate_meta: dict[int, dict[str, Any]] = {
        index: {
            "exact_duplicate": False,
            "duplicate_group": None,
            "duplicate_of": None,
            "near_duplicate": False,
            "near_duplicate_of": None,
            "near_duplicate_score": None,
        }
        for index in range(len(records))
    }

    exact_groups: dict[str, list[int]] = defaultdict(list)
    combined_texts: list[str] = []
    token_sets: list[set[str]] = []
    for index, record in enumerate(records):
        exact_key = "\n".join(
            [
                normalize_text(record.get("context")),
                normalize_text(record.get("question")),
                normalize_text(record.get("answer")),
            ]
        )
        exact_groups[exact_key].append(index)
        combined = normalize_whitespace(
            f"{normalize_text(record.get('context'))} {normalize_text(record.get('question'))}"
        )
        combined_texts.append(combined)
        token_sets.append(token_set(combined))

    group_number = 1
    for members in exact_groups.values():
        if len(members) < 2:
            continue
        group_id = f"exact_dup_{group_number:06d}"
        first_id = records[members[0]].get("question_id")
        for offset, index in enumerate(members):
            duplicate_meta[index]["exact_duplicate"] = offset > 0
            duplicate_meta[index]["duplicate_group"] = group_id
            duplicate_meta[index]["duplicate_of"] = None if offset == 0 else first_id
        group_number += 1

    near_pairs: list[dict[str, Any]] = []
    for left in range(len(records)):
        for right in range(left + 1, len(records)):
            if not combined_texts[left] or not combined_texts[right]:
                continue
            if combined_texts[left] == combined_texts[right]:
                continue

            token_score = jaccard(token_sets[left], token_sets[right])
            if token_score >= NEAR_DUPLICATE_JACCARD:
                ratio = SequenceMatcher(None, combined_texts[left], combined_texts[right]).ratio()
            else:
                quick_ratio = SequenceMatcher(
                    None, combined_texts[left], combined_texts[right]
                ).quick_ratio()
                if quick_ratio < NEAR_DUPLICATE_RATIO:
                    continue
                ratio = SequenceMatcher(None, combined_texts[left], combined_texts[right]).ratio()

            score = max(token_score, ratio)
            if ratio >= NEAR_DUPLICATE_RATIO or token_score >= NEAR_DUPLICATE_JACCARD:
                pair = {
                    "left_question_id": records[left].get("question_id"),
                    "right_question_id": records[right].get("question_id"),
                    "similarity": round(score, 4),
                }
                near_pairs.append(pair)
                duplicate_meta[right]["near_duplicate"] = True
                if duplicate_meta[right]["near_duplicate_of"] is None:
                    duplicate_meta[right]["near_duplicate_of"] = records[left].get("question_id")
                    duplicate_meta[right]["near_duplicate_score"] = round(score, 4)

    return duplicate_meta, near_pairs


def audit_records(raw_records: list[Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    audited: list[dict[str, Any]] = []
    malformed_indexes: list[int] = []
    assigned_question_ids = 0

    for index, raw_record in enumerate(raw_records, start=1):
        if isinstance(raw_record, dict):
            record = dict(raw_record)
        else:
            record = {"raw_record": raw_record}

        errors = validate_record(raw_record)
        if errors:
            malformed_indexes.append(index)

        if not isinstance(record.get("question_id"), str) or not record.get("question_id", "").strip():
            record["question_id"] = f"tennis_{index:06d}"
            assigned_question_ids += 1
        else:
            record["question_id"] = record["question_id"].strip()

        category, tags = infer_categories(record.get("context"), record.get("question"))
        record["category"] = category
        record["tags"] = tags
        record["audit_valid"] = not errors
        record["audit_errors"] = errors
        audited.append(record)

    question_id_counts = Counter(record["question_id"] for record in audited)
    duplicate_question_ids = sorted(
        question_id for question_id, count in question_id_counts.items() if count > 1
    )
    if duplicate_question_ids:
        duplicate_id_set = set(duplicate_question_ids)
        for record in audited:
            if record["question_id"] in duplicate_id_set:
                record["audit_valid"] = False
                record["audit_errors"].append("duplicate question_id")

    duplicate_meta, near_pairs = find_duplicates(audited)
    for index, record in enumerate(audited):
        record.update(duplicate_meta[index])

    valid_records = [record for record in audited if record["audit_valid"]]
    category_distribution = Counter(record["category"] for record in audited)
    answer_distribution = Counter(answer_key(record.get("answer")) for record in audited)
    tag_distribution = Counter(tag for record in audited for tag in record["tags"])

    exact_duplicate_records = sum(1 for record in audited if record["exact_duplicate"])
    near_duplicate_records = sum(1 for record in audited if record["near_duplicate"])

    summary: dict[str, Any] = {
        "input_record_count": len(raw_records),
        "valid_record_count": len(valid_records),
        "malformed_record_count": len(audited) - len(valid_records),
        "malformed_record_indexes": [
            index + 1 for index, record in enumerate(audited) if not record["audit_valid"]
        ],
        "assigned_question_id_count": assigned_question_ids,
        "duplicate_question_id_count": len(duplicate_question_ids),
        "duplicate_question_ids": duplicate_question_ids,
        "exact_duplicate_record_count": exact_duplicate_records,
        "near_duplicate_record_count": near_duplicate_records,
        "near_duplicate_pair_count": len(near_pairs),
        "near_duplicate_pairs_sample": near_pairs[:50],
        "category_distribution": dict(sorted(category_distribution.items())),
        "tag_distribution": dict(sorted(tag_distribution.items())),
        "answer_distribution": dict(sorted(answer_distribution.items())),
        "length_statistics": {
            "context": field_lengths(audited, "context"),
            "question": field_lengths(audited, "question"),
            "answer": field_lengths(audited, "answer"),
        },
    }
    return audited, summary


def markdown_table(rows: list[tuple[Any, Any]], headers: tuple[str, str]) -> str:
    lines = [f"| {headers[0]} | {headers[1]} |", "| --- | ---: |"]
    for key, value in rows:
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def write_report(path: Path, input_path: Path, output_path: Path, summary_path: Path, summary: dict[str, Any]) -> None:
    top_answers = Counter(summary["answer_distribution"]).most_common(25)
    category_rows = sorted(summary["category_distribution"].items())
    answer_rows = top_answers
    malformed_indexes = summary["malformed_record_indexes"][:50]

    limitations = [
        "Raw records only provide the minimal context/question/answer schema; provenance/source fields are not present.",
        "Categories and tags are rule-based labels, so ambiguous questions may need manual review before training.",
        "Near-duplicate detection is based on text similarity only and does not know template ids, match ids, or source clusters.",
        "The audit does not verify factual tennis correctness or whether each answer is entailed by the context.",
    ]

    report = [
        "# Tennis Raw Dataset Audit",
        "",
        "## Inputs and Outputs",
        "",
        f"- Input: `{input_path.as_posix()}`",
        f"- Audited dataset: `{output_path.as_posix()}`",
        f"- Summary JSON: `{summary_path.as_posix()}`",
        "",
        "## Record Counts",
        "",
        f"- Total examples: {summary['input_record_count']}",
        f"- Valid examples: {summary['valid_record_count']}",
        f"- Malformed examples: {summary['malformed_record_count']}",
        f"- Assigned question ids: {summary['assigned_question_id_count']}",
        f"- Exact duplicate records after first occurrence: {summary['exact_duplicate_record_count']}",
        f"- Near-duplicate records after first match: {summary['near_duplicate_record_count']}",
        f"- Near-duplicate pairs: {summary['near_duplicate_pair_count']}",
        "",
        "## Category Distribution",
        "",
        markdown_table(category_rows, ("Category", "Count")),
        "",
        "## Answer Distribution",
        "",
        markdown_table(answer_rows, ("Answer", "Count")),
        "",
        "## Length Statistics",
        "",
        "Length statistics are reported as characters and whitespace-token counts.",
        "",
        "```json",
        json.dumps(summary["length_statistics"], indent=2, sort_keys=True),
        "```",
        "",
        "## Malformed Records",
        "",
        (
            f"Malformed record indexes, first 50: {malformed_indexes}"
            if malformed_indexes
            else "No malformed records were detected."
        ),
        "",
        "## Main Limitations",
        "",
    ]
    report.extend(f"- {item}" for item in limitations)
    report.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    report_path = Path(args.report)
    summary_path = Path(args.summary)

    raw_records = load_json_array(input_path)
    audited, summary = audit_records(raw_records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(json.dumps(audited, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    write_report(report_path, input_path, output_path, summary_path, summary)

    print(f"Loaded {summary['input_record_count']} records from {input_path}")
    print(f"Valid records: {summary['valid_record_count']}")
    print(f"Malformed records: {summary['malformed_record_count']}")
    print(f"Exact duplicate records: {summary['exact_duplicate_record_count']}")
    print(f"Near-duplicate records: {summary['near_duplicate_record_count']}")
    print(f"Wrote audited data to {output_path}")
    print(f"Wrote report to {report_path}")
    print(f"Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()
