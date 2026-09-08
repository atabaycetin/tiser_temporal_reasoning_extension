"""M0 CLI - build the in-scope conflict subset (items.jsonl)."""

import argparse

from src.conflict.subset import build_subset
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="M0: build the conflict-probe subset.")
    parser.add_argument("--config", default="config/conflict.yaml")
    parser.add_argument("--test-file", default=None, help="override paths.test_file (e.g. local full-data JSONL)")
    parser.add_argument("--max-per-split", type=int, default=None, help="cap items per split (smoke/dev)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.test_file is not None:
        cfg.paths.test_file = args.test_file
    if args.max_per_split is not None:
        cfg.conflict.max_per_split = args.max_per_split

    build_subset(cfg)


if __name__ == "__main__":
    main()
