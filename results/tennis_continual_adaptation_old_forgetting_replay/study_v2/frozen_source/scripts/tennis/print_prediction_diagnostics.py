"""Print selected tennis prediction rows for parser/error inspection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.tennis.eval import load_predictions_jsonl


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    rows = load_predictions_jsonl(args.predictions)
    question_ids = set(args.question_id or [])

    printed = 0
    for row in rows:
        if question_ids and str(row.get("question_id")) not in question_ids:
            continue
        if args.only_errors and not is_error(row):
            continue
        print_row(row)
        printed += 1
        if args.limit is not None and printed >= args.limit:
            break

    if printed == 0:
        print("No matching prediction rows found.")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print tennis prediction rows with raw generation and prompt."
    )
    parser.add_argument("--predictions", required=True, help="Path to predictions.jsonl.")
    parser.add_argument(
        "--question-id",
        action="append",
        default=[],
        help="Question ID to print. Can be repeated.",
    )
    parser.add_argument(
        "--only-errors",
        action="store_true",
        help="Print only malformed rows or rows with em != 1.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Maximum rows to print.")
    return parser.parse_args(argv)


def is_error(row: dict[str, Any]) -> bool:
    if bool(row.get("malformed", False)):
        return True
    try:
        return float(row.get("em", 0.0)) != 1.0
    except (TypeError, ValueError):
        return True


def print_row(row: dict[str, Any]) -> None:
    print("=" * 80)
    for key in ("question_id", "category", "gold", "pred_answer", "malformed", "em", "f1"):
        print(f"{key}: {row.get(key, '')}")
    print("\nraw_generation:")
    print(row.get("raw_generation", ""))
    print("\nprompt:")
    print(row.get("prompt", ""))


if __name__ == "__main__":
    main()
