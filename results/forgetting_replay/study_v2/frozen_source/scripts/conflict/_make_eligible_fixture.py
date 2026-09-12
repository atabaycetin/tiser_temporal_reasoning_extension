"""Dev-only fixture: fabricate 'eligible.jsonl' from 'items.jsonl' for local M3/M4/M6 work.

The real eligible set is produced by M1 (GPU) + M2; it is not available on a laptop. Under
D-ANCHOR the kept set has m == answer_orig, so a faithful local stand-in is just a balanced
sample of M0 items with m := answer_orig, agreement := 1.0, n_malformed := 0. NOT part of the
pipeline, it only unblocks CPU development of the downstream stages.
"""

import argparse
import os
import random

from src.conflict.io import read_jsonl, stage_dir, write_jsonl
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Fabricate a local eligible.jsonl fixture.")
    parser.add_argument("--config", default="config/conflict.yaml")
    parser.add_argument("--per-split", type=int, default=60, help="items to sample per split")
    args = parser.parse_args()

    cfg = load_config(args.config)
    items = read_jsonl(os.path.join(stage_dir(cfg, "subset"), "items.jsonl"))
    rng = random.Random(cfg.seed)

    by_split: dict[str, list[dict]] = {}
    for it in items:
        by_split.setdefault(it["split"], []).append(it)

    eligible: list[dict] = []
    for split in sorted(by_split):
        rows = by_split[split]
        chosen = rows if len(rows) <= args.per_split else rng.sample(rows, args.per_split)
        for it in chosen:
            eligible.append({**it, "m": it["answer_orig"], "agreement": 1.0, "n_malformed": 0})

    out = os.path.join(stage_dir(cfg, "eligible"), "eligible.jsonl")
    write_jsonl(out, eligible)
    print(f"[fixture] wrote {len(eligible)} fake-eligible items -> {out}")
    print("[fixture] DEV ONLY - replace with the real M2 eligible.jsonl pulled from the pod.")


if __name__ == "__main__":
    main()
