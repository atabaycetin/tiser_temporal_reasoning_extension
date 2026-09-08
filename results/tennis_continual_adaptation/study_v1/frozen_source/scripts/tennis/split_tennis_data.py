"""Create deterministic train/dev/test splits for tennis temporal QA data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tennis.splits import load_records, split_records, write_split_files, write_split_statistics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split tennis temporal QA data.")
    parser.add_argument("--input", default="data/tennis/processed/tennis_all_tiser.json")
    parser.add_argument("--output-dir", default="data/tennis")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--dev-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--summary",
        default="results/tennis_domain_adaptation/processed/tennis_split_summary.json",
    )
    parser.add_argument(
        "--report",
        default="results/tennis_domain_adaptation/processed/tennis_split_report.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_records(args.input)
    splits, summary = split_records(
        records,
        train_ratio=args.train_ratio,
        dev_ratio=args.dev_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )
    split_paths = write_split_files(splits, args.output_dir)
    summary.update(
        {
            "input_path": str(Path(args.input)),
            "split_paths": split_paths,
            "summary_path": str(Path(args.summary)),
            "report_path": str(Path(args.report)),
        }
    )
    write_split_statistics(args.summary, args.report, summary)

    print(f"Loaded records: {summary['total_examples']}")
    print(f"Train/dev/test: {summary['split_counts']}")
    print(
        "Duplicate leakage: "
        f"{summary['duplicate_leakage_check']['has_leakage']} "
        f"({summary['duplicate_leakage_check']['leaked_duplicate_group_count']} groups)"
    )
    print(f"Wrote train split: {split_paths['train']}")
    print(f"Wrote dev split: {split_paths['dev']}")
    print(f"Wrote test split: {split_paths['test']}")
    print(f"Wrote summary: {args.summary}")
    print(f"Wrote report: {args.report}")


if __name__ == "__main__":
    main()
