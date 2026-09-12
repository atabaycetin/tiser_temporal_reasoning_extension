"""Significance stats for the run matrix (backs the report's CI/McNemar claims).

Reads the scored cells ('outputs/conflict/scored/<model>__<style>.jsonl') and computes,
on faithful-EM: a paired bootstrap 95% CI per cell and per axis contrast, and a
continuity-corrected McNemar chi-square for the prompt axis (tiser vs standard, both
on the fine-tuned model) and the model axis (fine-tuned vs base, both under the TISER
prompt). Rows are paired by (id, conflict_type) across cells.

Output: 'outputs/conflict/stats/stats.json' + run_meta. CPU only, stdlib only.
"""

from __future__ import annotations

import argparse
import os
import random

from src.conflict.io import read_jsonl, stage_dir, write_run_meta
from src.utils.config import load_config
from src.utils.io import write_json

CELLS = ["tiser__tiser", "tiser__standard", "base__tiser", "base__standard"]
AXES = {
    "prompt_axis": ("tiser__tiser", "tiser__standard"),
    "model_axis": ("tiser__tiser", "base__tiser"),
}
N_BOOT = 2000


def _bootstrap_ci(stat, n: int, rng: random.Random) -> list[float]:
    vals = sorted(stat([rng.randrange(n) for _ in range(n)]) for _ in range(N_BOOT))
    return [vals[int(0.025 * N_BOOT)], vals[int(0.975 * N_BOOT)]]


def _mcnemar(a: list[float], b: list[float]) -> dict:
    only_a = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    only_b = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    chi2 = (abs(only_a - only_b) - 1) ** 2 / (only_a + only_b)
    return {"discordant_first_only": only_a, "discordant_second_only": only_b, "chi2_cc": chi2}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/conflict.yaml")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    cfg = load_config(args.config)

    scored = stage_dir(cfg, "scored")
    em: dict[str, list[float]] = {}
    keys = None
    for cell in CELLS:
        rows = read_jsonl(os.path.join(scored, f"{cell}.jsonl"))
        keyed = {(r["id"], r["conflict_type"]): r["faithful_em"] for r in rows}
        if len(keyed) != len(rows):
            raise ValueError(f"{cell}: duplicate (id, conflict_type) keys")
        if keys is None:
            keys = sorted(keyed)
        elif sorted(keyed) != keys:
            raise ValueError(f"{cell}: row keys do not match the other cells")
        em[cell] = [keyed[k] for k in keys]
    n = len(keys)

    rng = random.Random(args.seed)
    cells_out = {}
    for cell in CELLS:
        v = em[cell]
        cells_out[cell] = {
            "faithful_em": sum(v) / n,
            "ci95": _bootstrap_ci(lambda idx: sum(v[i] for i in idx) / n, n, rng),
        }

    axes_out = {}
    for name, (first, second) in AXES.items():
        a, b = em[first], em[second]
        axes_out[name] = {
            "cells": [first, second],
            "delta_faithful_em": sum(a) / n - sum(b) / n,
            "ci95": _bootstrap_ci(lambda idx: sum(a[i] - b[i] for i in idx) / n, n, rng),
            "mcnemar": _mcnemar(a, b),
        }

    out_dir = stage_dir(cfg, "stats")
    result = {
        "n_rows": n,
        "metric": "faithful_em",
        "bootstrap": {"resamples": N_BOOT, "seed": args.seed, "paired": True},
        "cells": cells_out,
        "axes": axes_out,
    }
    write_json(os.path.join(out_dir, "stats.json"), result)
    write_run_meta(out_dir, cfg, extra={"inputs": [f"scored/{c}.jsonl" for c in CELLS]})

    for cell in CELLS:
        c = cells_out[cell]
        print(f"{cell}: faithful-EM {c['faithful_em']:.4f}  CI95 [{c['ci95'][0]:.3f}, {c['ci95'][1]:.3f}]")
    for name, ax in axes_out.items():
        m = ax["mcnemar"]
        print(
            f"{name}: delta {ax['delta_faithful_em']:+.4f}  CI95 [{ax['ci95'][0]:+.3f}, {ax['ci95'][1]:+.3f}]  "
            f"McNemar chi2 {m['chi2_cc']:.1f} ({m['discordant_first_only']} vs {m['discordant_second_only']})"
        )
    print(f"wrote -> {out_dir}")


if __name__ == "__main__":
    main()
