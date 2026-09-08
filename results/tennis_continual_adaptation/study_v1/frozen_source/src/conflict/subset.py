"""M0 - build the in-scope conflict subset.

Parses the in-scope splits (TimeQA easy/hard, TempReason L2/L3), isolates and
structure-parses each context, derives the closed-book prompt, and tags the
conflict classes applicable to each item. TGQA / ToT are out of scope (synthetic
or fictional entities -> no parametric memory to conflict with).

Output: 'outputs/conflict/subset/items.jsonl' (+ 'subset_report.json', 'run_meta.json').
"""

from __future__ import annotations

import os
import random
import statistics

from src.conflict.context_parse import (
    applicable_classes,
    isolate_context,
    parse_context,
    strip_context,
)
from src.conflict.io import load_records, stage_dir, write_jsonl, write_run_meta
from src.utils.io import write_json


def _cap_per_split(records: list[dict], n: int, seed: int) -> list[dict]:
    """Seeded down-sample to <= n records per split (for smoke/dev runs)."""
    rng = random.Random(seed)
    by_split: dict[str, list[dict]] = {}
    for r in records:
        by_split.setdefault(r["dataset_name"], []).append(r)
    kept: list[dict] = []
    for split in sorted(by_split):
        rows = by_split[split]
        kept.extend(rows if len(rows) <= n else rng.sample(rows, n))
    return kept


def build_subset(cfg) -> dict:
    # M0's only stochastic step (the dev-cap sampler) uses a local seeded RNG, so no
    # global set_seed here -- that keeps M0 free of the GPU stack (numpy/torch).
    in_scope = set(cfg.conflict.in_scope_splits)

    records = [r for r in load_records(cfg.paths.test_file) if r["dataset_name"] in in_scope]
    if not records:
        raise ValueError(
            f"no in-scope records found in {cfg.paths.test_file} "
            f"(expected any of {sorted(in_scope)}); is the data fetched / LFS pulled?"
        )
    if cfg.conflict.max_per_split is not None:
        records = _cap_per_split(records, cfg.conflict.max_per_split, cfg.seed)

    items: list[dict] = []
    for r in records:
        split = r["dataset_name"]
        # Hard-fail with the offending id: M0 guarantees a 100%-parsed subset, so a
        # parse error means the template assumption broke and must be fixed, not skipped.
        ctx_raw = isolate_context(r["prompt"])
        ctx_events = parse_context(split, ctx_raw)
        prompt_no_context = strip_context(r["prompt"])
        items.append(
            {
                "id": r["question_id"],
                "split": split,
                "q_type": split.removesuffix("_test"),
                "q": r["question"],
                "answer_orig": r["answer"],
                "ctx_raw": ctx_raw,
                "ctx_events": ctx_events,
                "prompt_no_context": prompt_no_context,
                "applicable_classes": applicable_classes(split),
            }
        )

    out_dir = stage_dir(cfg, "subset")
    write_jsonl(os.path.join(out_dir, "items.jsonl"), items)
    report = _report(items)
    write_json(os.path.join(out_dir, "subset_report.json"), report)
    write_run_meta(out_dir, cfg)

    print(f"[M0] built {len(items)} items -> {out_dir}/items.jsonl")
    print(f"[M0] per split: {report['per_split']}")
    print(f"[M0] applicable per class: {report['per_class']}")
    return report


def _report(items: list[dict]) -> dict:
    per_split: dict[str, int] = {}
    per_class: dict[str, int] = {}
    n_events: list[int] = []
    for it in items:
        per_split[it["split"]] = per_split.get(it["split"], 0) + 1
        for c in it["applicable_classes"]:
            per_class[c] = per_class.get(c, 0) + 1
        n_events.append(len(it["ctx_events"]))
    return {
        "n_total": len(items),
        "per_split": dict(sorted(per_split.items())),
        "per_class": dict(sorted(per_class.items())),
        "events_per_item": {
            "min": min(n_events) if n_events else 0,
            "median": statistics.median(n_events) if n_events else 0,
            "max": max(n_events) if n_events else 0,
        },
    }
