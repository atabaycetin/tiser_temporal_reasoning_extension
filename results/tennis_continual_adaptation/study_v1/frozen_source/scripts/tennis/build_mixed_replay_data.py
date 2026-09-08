"""Build a tennis + original TISER replay training set.

The script copies all input rows before editing metadata, samples replay rows
deterministically, shuffles deterministically, and never writes back to either
source file.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    args = parse_args()
    tennis_path = resolve_repo_path(args.tennis_train)
    tiser_path = resolve_repo_path(args.tiser_train)
    output_path = resolve_repo_path(args.output)
    summary_path = resolve_repo_path(args.summary)

    tennis_rows = load_records(tennis_path)
    tiser_rows = load_records(tiser_path)
    if args.tiser_replay_size > len(tiser_rows):
        raise ValueError(
            f"--tiser-replay-size {args.tiser_replay_size} exceeds available "
            f"TISER train rows ({len(tiser_rows)})"
        )

    rng = random.Random(args.seed)
    replay_rows = rng.sample(tiser_rows, args.tiser_replay_size)

    mixed_rows = (
        [prepare_tennis_row(row) for row in tennis_rows]
        + [prepare_tiser_row(row) for row in replay_rows]
    )
    rng.shuffle(mixed_rows)

    summary = build_summary(
        tennis_path=tennis_path,
        tiser_path=tiser_path,
        output_path=output_path,
        seed=args.seed,
        requested_tiser_replay_size=args.tiser_replay_size,
        tennis_count=len(tennis_rows),
        tiser_replay_count=len(replay_rows),
        mixed_rows=mixed_rows,
    )

    write_json(output_path, mixed_rows)
    write_json(summary_path, summary)
    print(f"[mixed-replay] tennis rows: {len(tennis_rows)}")
    print(f"[mixed-replay] TISER replay rows: {len(replay_rows)}")
    print(f"[mixed-replay] total mixed rows: {len(mixed_rows)}")
    print(f"[mixed-replay] wrote {relative_or_absolute(output_path)}")
    print(f"[mixed-replay] wrote {relative_or_absolute(summary_path)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build tennis + TISER replay train JSON.")
    parser.add_argument("--tennis-train", required=True)
    parser.add_argument("--tiser-train", required=True)
    parser.add_argument("--tiser-replay-size", type=int, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()
    if args.tiser_replay_size < 0:
        parser.error("--tiser-replay-size must be non-negative")
    return args


def resolve_repo_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return REPO_ROOT / value


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")
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


def prepare_tennis_row(row: dict[str, Any]) -> dict[str, Any]:
    copied = dict(row)
    copied["dataset_name"] = str(copied.get("dataset_name") or "tennis_temporal")
    copied["replay_source"] = "tennis"
    return copied


def prepare_tiser_row(row: dict[str, Any]) -> dict[str, Any]:
    copied = dict(row)
    copied["dataset_name"] = str(copied.get("dataset_name") or "tiser_replay")
    copied["replay_source"] = "tiser_original"
    return copied


def build_summary(
    *,
    tennis_path: Path,
    tiser_path: Path,
    output_path: Path,
    seed: int,
    requested_tiser_replay_size: int,
    tennis_count: int,
    tiser_replay_count: int,
    mixed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    dataset_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    dataset_category_counts: dict[str, Counter[str]] = defaultdict(Counter)
    source_counts: Counter[str] = Counter()

    for row in mixed_rows:
        dataset_name = str(row.get("dataset_name") or "unknown")
        category = str(row.get("category") or "unknown")
        source = str(row.get("replay_source") or "unknown")
        dataset_counts[dataset_name] += 1
        category_counts[category] += 1
        dataset_category_counts[dataset_name][category] += 1
        source_counts[source] += 1

    return {
        "tennis_train": relative_or_absolute(tennis_path),
        "tiser_train": relative_or_absolute(tiser_path),
        "output": relative_or_absolute(output_path),
        "seed": seed,
        "requested_tiser_replay_size": requested_tiser_replay_size,
        "tennis_records": tennis_count,
        "tiser_replay_records": tiser_replay_count,
        "total_records": len(mixed_rows),
        "counts_by_source": dict(sorted(source_counts.items())),
        "counts_by_dataset_name": dict(sorted(dataset_counts.items())),
        "counts_by_category": dict(sorted(category_counts.items())),
        "counts_by_dataset_name_category": {
            dataset: dict(sorted(category_counter.items()))
            for dataset, category_counter in sorted(dataset_category_counts.items())
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def relative_or_absolute(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
