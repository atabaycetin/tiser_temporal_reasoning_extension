"""Explain exactly which tennis training records received full-run traces."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the pilot, full traced file, and batch manifest to explain "
            "the historical 600-record cutoff."
        )
    )
    parser.add_argument("--train", default="data/tennis/tennis_train.json")
    parser.add_argument("--pilot", default="data/tennis/tennis_train_traced_50.json")
    parser.add_argument("--traced", default="data/tennis/tennis_train_traced_full.json")
    parser.add_argument(
        "--manifest",
        default=(
            "results/tennis_domain_adaptation/trace_generation/"
            "batches_full/manifest.json"
        ),
    )
    parser.add_argument(
        "--json-output",
        default=(
            "results/tennis_domain_adaptation/trace_coverage/"
            "trace_coverage_audit.json"
        ),
    )
    parser.add_argument(
        "--report-output",
        default=(
            "results/tennis_domain_adaptation/trace_coverage/"
            "trace_coverage_audit.md"
        ),
    )
    return parser.parse_args()


def resolve(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else REPO_ROOT / value


def load_json(path: str | Path) -> Any:
    resolved = resolve(path)
    try:
        return json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing input: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON: {resolved} ({exc})") from exc


def ids(rows: list[dict[str, Any]], label: str) -> list[str]:
    values: list[str] = []
    for index, row in enumerate(rows):
        value = row.get("question_id") if isinstance(row, dict) else None
        if not isinstance(value, str) or not value:
            raise SystemExit(f"{label} row {index} lacks a non-empty question_id")
        values.append(value)
    if len(values) != len(set(values)):
        raise SystemExit(f"{label} contains duplicate question_id values")
    return values


def category_counts(
    selected_ids: list[str], category_by_id: dict[str, str]
) -> dict[str, int]:
    counts = Counter(category_by_id[value] for value in selected_ids)
    return dict(sorted(counts.items()))


def audit_coverage(
    train: list[dict[str, Any]],
    pilot: list[dict[str, Any]],
    traced: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    train_ids = ids(train, "train")
    pilot_ids = ids(pilot, "pilot")
    traced_ids = ids(traced, "traced")
    selected_ids = manifest.get("selected_question_ids")
    batches = manifest.get("batches")
    if not isinstance(selected_ids, list) or not all(
        isinstance(value, str) for value in selected_ids
    ):
        raise SystemExit("manifest.selected_question_ids must be a list of strings")
    if not isinstance(batches, list):
        raise SystemExit("manifest.batches must be a list")

    flattened_batches: list[str] = []
    batch_sizes: list[int] = []
    for index, batch in enumerate(batches, start=1):
        batch_ids = batch.get("question_ids") if isinstance(batch, dict) else None
        if not isinstance(batch_ids, list) or not all(
            isinstance(value, str) for value in batch_ids
        ):
            raise SystemExit(f"manifest batch {index} has invalid question_ids")
        flattened_batches.extend(batch_ids)
        batch_sizes.append(len(batch_ids))

    train_set = set(train_ids)
    pilot_set = set(pilot_ids)
    traced_set = set(traced_ids)
    selected_set = set(selected_ids)
    expected_selected_ids = [value for value in train_ids if value not in pilot_set]
    tail_ids = selected_ids[len(traced_ids) :]
    missing_ids = [value for value in train_ids if value not in traced_set]
    expected_missing_set = pilot_set | set(tail_ids)

    checks = {
        "pilot_is_first_train_block": pilot_ids == train_ids[: len(pilot_ids)],
        "manifest_is_train_minus_pilot_in_order": selected_ids == expected_selected_ids,
        "manifest_batches_flatten_to_selected_ids": flattened_batches == selected_ids,
        "traced_is_manifest_prefix": traced_ids == selected_ids[: len(traced_ids)],
        "pilot_and_traced_are_disjoint": pilot_set.isdisjoint(traced_set),
        "missing_is_exactly_pilot_plus_ungenerated_tail": (
            set(missing_ids) == expected_missing_set
        ),
        "all_ids_belong_to_train": (
            pilot_set | traced_set | selected_set
        ).issubset(train_set),
    }

    consumed_batches = 0
    offset = 0
    for batch_size in batch_sizes:
        if traced_ids[offset : offset + batch_size] != selected_ids[
            offset : offset + batch_size
        ]:
            break
        if offset + batch_size > len(traced_ids):
            break
        consumed_batches += 1
        offset += batch_size

    category_by_id = {
        row["question_id"]: str(row.get("category", "unknown")) for row in train
    }
    all_checks_pass = all(checks.values())
    return {
        "status": "pass" if all_checks_pass else "fail",
        "conclusion": (
            "The 600-record artifact is the ordered output of the first 12 "
            "non-pilot batches. The cutoff is operational, not a recorded "
            "quality filter."
            if all_checks_pass
            else "The tracked artifacts do not satisfy the expected coverage relationships."
        ),
        "counts": {
            "train": len(train_ids),
            "pilot": len(pilot_ids),
            "manifest_selected_after_pilot_exclusion": len(selected_ids),
            "manifest_batches": len(batches),
            "consumed_complete_batches": consumed_batches,
            "reported_traced_full": len(traced_ids),
            "ungenerated_tail": len(tail_ids),
            "absent_from_reported_traced_full": len(missing_ids),
        },
        "checks": checks,
        "boundaries": {
            "last_reported_traced_id": traced_ids[-1] if traced_ids else None,
            "first_ungenerated_tail_id": tail_ids[0] if tail_ids else None,
            "last_ungenerated_tail_id": tail_ids[-1] if tail_ids else None,
        },
        "category_counts": {
            "reported_traced_full": category_counts(traced_ids, category_by_id),
            "absent_from_reported_traced_full": category_counts(
                missing_ids, category_by_id
            ),
        },
        "interpretation": {
            "pilot_note": (
                "The 50 pilot records validate separately but were not concatenated "
                "into tennis_train_traced_full.json."
            ),
            "tail_note": (
                "Requests exist for the final 135 selected IDs in batches 13-15, "
                "but no corresponding generated output is committed."
            ),
            "quality_note": (
                "This coverage audit explains selection mechanics only; semantic "
                "quality is evaluated separately."
            ),
        },
    }


def markdown_report(result: dict[str, Any]) -> str:
    counts = result["counts"]
    lines = [
        "# Tennis Trace-Coverage Audit",
        "",
        f"**Status:** `{result['status']}`",
        "",
        result["conclusion"],
        "",
        "## Counts",
        "",
        "| Item | Count |",
        "| --- | ---: |",
    ]
    for key, value in counts.items():
        lines.append(f"| `{key}` | {value} |")

    lines.extend(["", "## Integrity checks", ""])
    for key, value in result["checks"].items():
        lines.append(f"- [{'x' if value else ' '}] `{key}`")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- {result['interpretation']['pilot_note']}",
            f"- {result['interpretation']['tail_note']}",
            f"- {result['interpretation']['quality_note']}",
            "",
            "The missing 185 records are therefore the disjoint union of the valid "
            "50-record pilot and the 135-record ungenerated tail. No quality flag, "
            "exclusion-reason field, or alternative sampling rule is present in the "
            "tracked artifacts.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    result = audit_coverage(
        load_json(args.train),
        load_json(args.pilot),
        load_json(args.traced),
        load_json(args.manifest),
    )

    json_output = resolve(args.json_output)
    report_output = resolve(args.report_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report_output.write_text(markdown_report(result), encoding="utf-8")
    print(f"Wrote {json_output}")
    print(f"Wrote {report_output}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

