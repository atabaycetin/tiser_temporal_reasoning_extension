"""M1 CLI - closed-book memory elicitation (GPU).

Runs once per model entry in config.conflict.memory.models (use --only-model to
run a single one, e.g. the cheap 'base' cross-check first).
"""

import argparse

from src.conflict.memory import elicit_memory
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="M1: closed-book parametric-memory elicitation.")
    parser.add_argument("--config", default="config/conflict.yaml")
    parser.add_argument("--only-model", default=None, help="run a single model entry by tag (e.g. base|tiser)")
    parser.add_argument("--closed-book-style", default=None, help="override memory.closed_book_style")
    parser.add_argument("--max-per-split", type=int, default=None, help="cap items per split (smoke)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.closed_book_style is not None:
        cfg.conflict.memory.closed_book_style = args.closed_book_style

    items = None
    if args.max_per_split is not None:
        # Re-derive a capped item list from the built subset without rebuilding it.
        from src.conflict.io import read_jsonl, stage_dir
        import os, random

        all_items = read_jsonl(os.path.join(stage_dir(cfg, "subset"), "items.jsonl"))
        rng = random.Random(cfg.seed)
        by_split: dict[str, list[dict]] = {}
        for it in all_items:
            by_split.setdefault(it["split"], []).append(it)
        items = []
        for split in sorted(by_split):
            rows = by_split[split]
            items.extend(rows if len(rows) <= args.max_per_split else rng.sample(rows, args.max_per_split))

    elicit_memory(cfg, items=items, only_tag=args.only_model)


if __name__ == "__main__":
    main()
