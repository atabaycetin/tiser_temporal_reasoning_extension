"""Deterministic split utilities for tennis temporal QA datasets."""

from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SPLIT_NAMES = ("train", "dev", "test")
LOW_CATEGORY_THRESHOLD = 30
LOW_DATASET_THRESHOLD = 800


def load_records(path: Path | str) -> list[dict[str, Any]]:
    input_path = Path(path)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {input_path}")

    records: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Record {index} is not a JSON object")
        records.append(item)
    return records


def write_records(path: Path | str, records: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def duplicate_key(record: dict[str, Any]) -> str:
    return "\n".join(
        [
            normalize_text(record.get("prompt")),
            normalize_text(record.get("question")),
            normalize_text(record.get("answer")),
        ]
    )


def group_by_category(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("category", "unknown"))].append(record)
    return dict(sorted(grouped.items()))


def build_duplicate_units(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    by_key: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        by_key[duplicate_key(record)].append(index)

    units: list[dict[str, Any]] = []
    warnings: list[str] = []
    for unit_number, (key, indices) in enumerate(sorted(by_key.items()), start=1):
        category_counts = Counter(str(records[index].get("category", "unknown")) for index in indices)
        categories = sorted(category_counts)
        category = sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        if len(categories) > 1:
            warnings.append(
                f"Duplicate unit {unit_number} spans multiple categories: {', '.join(categories)}"
            )

        units.append(
            {
                "unit_id": f"dup_unit_{unit_number:06d}",
                "key": key,
                "indices": indices,
                "category": category,
                "size": len(indices),
                "categories": categories,
            }
        )
    return units, warnings


def _allocate_counts(total: int, train_ratio: float, dev_ratio: float, test_ratio: float) -> dict[str, int]:
    if total <= 0:
        return {"train": 0, "dev": 0, "test": 0}
    if total == 1:
        return {"train": 1, "dev": 0, "test": 0}
    if total == 2:
        return {"train": 1, "dev": 0, "test": 1}

    ratios = {"train": train_ratio, "dev": dev_ratio, "test": test_ratio}
    raw_counts = {split: total * ratio for split, ratio in ratios.items()}
    counts = {split: int(raw_counts[split]) for split in SPLIT_NAMES}
    remaining = total - sum(counts.values())
    by_remainder = sorted(
        SPLIT_NAMES,
        key=lambda split: (raw_counts[split] - counts[split], ratios[split], split),
        reverse=True,
    )
    for split in by_remainder[:remaining]:
        counts[split] += 1

    for split in ("dev", "test"):
        if ratios[split] > 0 and counts[split] == 0:
            donor = max(SPLIT_NAMES, key=lambda name: counts[name])
            if counts[donor] > 1:
                counts[donor] -= 1
                counts[split] += 1

    return counts


def split_records(
    records: list[dict[str, Any]],
    *,
    train_ratio: float,
    dev_ratio: float,
    test_ratio: float,
    seed: int,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    ratio_sum = train_ratio + dev_ratio + test_ratio
    if abs(ratio_sum - 1.0) > 1e-8:
        raise ValueError(f"Split ratios must sum to 1.0, got {ratio_sum}")

    units, unit_warnings = build_duplicate_units(records)
    units_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        units_by_category[unit["category"]].append(unit)

    rng = random.Random(seed)
    split_units: dict[str, list[dict[str, Any]]] = {split: [] for split in SPLIT_NAMES}
    allocation_by_category: dict[str, dict[str, int]] = {}

    for category in sorted(units_by_category):
        category_units = list(units_by_category[category])
        rng.shuffle(category_units)
        counts = _allocate_counts(len(category_units), train_ratio, dev_ratio, test_ratio)
        allocation_by_category[category] = counts

        start = 0
        for split in SPLIT_NAMES:
            end = start + counts[split]
            split_units[split].extend(category_units[start:end])
            start = end

    split_records_by_name: dict[str, list[dict[str, Any]]] = {}
    for split in SPLIT_NAMES:
        indices: list[int] = []
        for unit in split_units[split]:
            indices.extend(unit["indices"])
        split_records_by_name[split] = [records[index] for index in sorted(indices)]

    summary = build_split_summary(
        records,
        split_records_by_name,
        split_units,
        allocation_by_category,
        seed=seed,
        train_ratio=train_ratio,
        dev_ratio=dev_ratio,
        test_ratio=test_ratio,
        unit_warnings=unit_warnings,
    )
    return split_records_by_name, summary


def _distribution(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts = Counter(str(record.get(field, "unknown")) for record in records)
    return dict(sorted(counts.items()))


def check_duplicate_leakage(split_records_by_name: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    key_to_splits: dict[str, set[str]] = defaultdict(set)
    key_to_ids: dict[str, list[str]] = defaultdict(list)
    for split, records in split_records_by_name.items():
        for record in records:
            key = duplicate_key(record)
            key_to_splits[key].add(split)
            key_to_ids[key].append(str(record.get("question_id", "")))

    leaked = []
    for key, splits in key_to_splits.items():
        if len(splits) > 1:
            leaked.append(
                {
                    "splits": sorted(splits),
                    "question_ids": sorted(question_id for question_id in key_to_ids[key] if question_id),
                }
            )

    return {
        "has_leakage": bool(leaked),
        "leaked_duplicate_group_count": len(leaked),
        "leaked_duplicate_groups": leaked[:100],
    }


def build_split_summary(
    all_records: list[dict[str, Any]],
    split_records_by_name: dict[str, list[dict[str, Any]]],
    split_units: dict[str, list[dict[str, Any]]],
    allocation_by_category: dict[str, dict[str, int]],
    *,
    seed: int,
    train_ratio: float,
    dev_ratio: float,
    test_ratio: float,
    unit_warnings: list[str],
) -> dict[str, Any]:
    total_count = len(all_records)
    split_counts = {split: len(split_records_by_name[split]) for split in SPLIT_NAMES}
    category_distribution = {
        split: _distribution(split_records_by_name[split], "category") for split in SPLIT_NAMES
    }
    answer_distribution = {
        split: _distribution(split_records_by_name[split], "answer") for split in SPLIT_NAMES
    }
    category_totals = _distribution(all_records, "category")
    low_category_warnings = [
        f"Category {category} has only {count} examples; per-category conclusions will be weak."
        for category, count in category_totals.items()
        if count < LOW_CATEGORY_THRESHOLD
    ]
    dataset_size_warning = (
        "The current dataset is useful for smoke/preliminary experiments but weak for final domain-adaptation conclusions. Consider expanding to 800-1500 examples balanced by category."
        if total_count < LOW_DATASET_THRESHOLD
        else None
    )
    leakage = check_duplicate_leakage(split_records_by_name)
    warnings = list(unit_warnings) + low_category_warnings
    if dataset_size_warning:
        warnings.append(dataset_size_warning)
    if leakage["has_leakage"]:
        warnings.append("Exact duplicate leakage was detected across splits.")

    recommendation = (
        "More data is recommended for low-count categories before final domain-adaptation conclusions."
        if low_category_warnings
        else "Dataset size is above the smoke-test threshold; still review category balance and duplicate groups before final claims."
    )
    if dataset_size_warning:
        recommendation = dataset_size_warning

    return {
        "total_examples": total_count,
        "seed": seed,
        "ratios": {"train": train_ratio, "dev": dev_ratio, "test": test_ratio},
        "split_counts": split_counts,
        "duplicate_unit_counts": {split: len(split_units[split]) for split in SPLIT_NAMES},
        "category_distribution": category_distribution,
        "answer_distribution": answer_distribution,
        "category_totals": category_totals,
        "allocation_by_category_unit_count": allocation_by_category,
        "duplicate_leakage_check": leakage,
        "warnings": warnings,
        "recommendation": recommendation,
    }


def markdown_table(distribution: dict[str, int], headers: tuple[str, str]) -> str:
    lines = [f"| {headers[0]} | {headers[1]} |", "| --- | ---: |"]
    for key, value in distribution.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def write_split_statistics(
    summary_path: Path | str,
    report_path: Path | str,
    summary: dict[str, Any],
) -> None:
    summary_output = Path(summary_path)
    report_output = Path(report_path)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )

    report_lines = [
        "# Tennis Dataset Split Report",
        "",
        f"- Total examples: {summary['total_examples']}",
        f"- Seed: {summary['seed']}",
        f"- Requested ratios: train {summary['ratios']['train']}, dev {summary['ratios']['dev']}, test {summary['ratios']['test']}",
        "",
        "## Split Counts",
        "",
        markdown_table(summary["split_counts"], ("Split", "Examples")),
        "",
        "## Category Distribution Per Split",
        "",
    ]
    for split in SPLIT_NAMES:
        report_lines.extend(
            [
                f"### {split}",
                "",
                markdown_table(summary["category_distribution"][split], ("Category", "Examples")),
                "",
            ]
        )

    report_lines.extend(["## Answer Distribution Per Split", ""])
    for split in SPLIT_NAMES:
        top_answers = dict(Counter(summary["answer_distribution"][split]).most_common(25))
        report_lines.extend(
            [
                f"### {split}",
                "",
                markdown_table(top_answers, ("Answer", "Examples")),
                "",
            ]
        )

    leakage = summary["duplicate_leakage_check"]
    report_lines.extend(
        [
            "## Duplicate Leakage Check",
            "",
            f"- Exact duplicate leakage detected: {leakage['has_leakage']}",
            f"- Leaked duplicate groups: {leakage['leaked_duplicate_group_count']}",
            "",
            "## Warnings",
            "",
        ]
    )
    if summary["warnings"]:
        report_lines.extend(f"- {warning}" for warning in summary["warnings"])
    else:
        report_lines.append("- No split warnings.")

    report_lines.extend(["", "## Recommendation", "", summary["recommendation"], ""])
    report_output.write_text("\n".join(report_lines), encoding="utf-8")


def write_split_files(
    split_records_by_name: dict[str, list[dict[str, Any]]],
    output_dir: Path | str,
) -> dict[str, str]:
    output_root = Path(output_dir)
    paths = {
        "train": output_root / "tennis_train.json",
        "dev": output_root / "tennis_dev.json",
        "test": output_root / "tennis_test.json",
    }
    for split, path in paths.items():
        write_records(path, split_records_by_name[split])
    return {split: str(path) for split, path in paths.items()}
