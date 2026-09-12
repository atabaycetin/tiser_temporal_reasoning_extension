"""M10 (analysis): does memory confidence drive conflict-raising in <reflection>?

Question: among the conflict items whose reflection *raised* the context<->memory
conflict (per the LLM-agent audit, the realized M7 judge), what was the model's
*initial closed-book memory confidence* (3/5, 4/5, 5/5 self-consistency passes at M1)?
Does the model only flag the mismatch for the facts it is most sure of (5/5)?

Joins the agentic reflection audit (outputs/conflict/scored/audit/<cell>.audit.csv)
to the M1/M2 memory confidence (the agreement field in eligible.jsonl, where
0.6 == 3/5, 0.8 == 4/5, 1.0 == 5/5) by item id, then cross-tabs confidence x
agent-raised, overall and stratified by conflict_type. tiser__tiser is the primary
(star) cell; base__tiser is reported as a secondary cross-check.

Output: outputs/conflict/confidence_vs_reflection/ ->
  - confidence_vs_reflection.json  (full result; backs the report's new H2 numbers)
  - raised_rows.csv                (every conflict-raised row, for inspection)
  - confidence_vs_reflection.png   (raise-rate by confidence bucket, per cell + within-C3)
  - run_meta.json                  (provenance)

CPU / laptop only. Reads existing artifacts; generates nothing.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.conflict.io import read_jsonl, stage_dir, write_run_meta
from src.utils.config import load_config
from src.utils.io import write_json

# Cells to analyse; the first is the primary (star) cell.
CELLS = ["tiser__tiser", "base__tiser"]
CONF_BUCKETS = ["3/5", "4/5", "5/5"]
CONFLICT_TYPES = ["C1", "C2", "C3", "control"]
_TRUE = {"1", "1.0", "true", "True"}


def _k5(agreement: float) -> str:
    """0.6 -> '3/5', 0.8 -> '4/5', 1.0 -> '5/5' (k self-consistent passes out of 5)."""
    return f"{round(agreement * 5)}/5"


def _is_true(v: str) -> bool:
    return str(v).strip() in _TRUE


def _outcome(row: dict) -> str:
    """How the answer landed: followed context (faith), reverted to memory (mem), or neither."""
    if str(row.get("faithful_em", "")).startswith("1"):
        return "faithful"
    if str(row.get("memorised_em", "")).startswith("1"):
        return "memorised"
    return "other"


def _rate(raised: int, total: int) -> float:
    return raised / total if total else 0.0


def analyse_cell(rows: list[dict], agreement: dict[str, float]) -> dict:
    """Cross-tab confidence x agent-raised for one (model x prompt) cell."""
    n_unmatched = sum(1 for r in rows if r["id"] not in agreement)

    # confidence-bucket x [total, raised], overall and per conflict_type
    overall: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_type: dict[str, dict[str, list[int]]] = {
        ct: defaultdict(lambda: [0, 0]) for ct in CONFLICT_TYPES
    }
    per_type_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # ct -> [total, raised]
    raised_rows: list[dict] = []

    for r in rows:
        agr = agreement.get(r["id"])
        if agr is None:
            continue
        bucket = _k5(agr)
        ctype = r["conflict_type"]
        raised = _is_true(r["agent_reflection_conflict_audit"])

        overall[bucket][0] += 1
        per_type_totals[ctype][0] += 1
        if ctype in by_type:
            by_type[ctype][bucket][0] += 1
        if raised:
            overall[bucket][1] += 1
            per_type_totals[ctype][1] += 1
            if ctype in by_type:
                by_type[ctype][bucket][1] += 1
            raised_rows.append(r)

    n_total = sum(t for t, _ in overall.values())
    n_raised = len(raised_rows)

    def fmt_buckets(tab: dict[str, list[int]]) -> dict:
        out = {}
        for b in CONF_BUCKETS:
            total, raised = tab.get(b, [0, 0])
            out[b] = {"rows": total, "raised": raised, "rate": _rate(raised, total)}
        return out

    return {
        "n_rows": n_total,
        "n_raised": n_raised,
        "agent_rate_overall": _rate(n_raised, n_total),
        "n_unmatched_ids": n_unmatched,
        "by_confidence": fmt_buckets(overall),
        "by_conflict_type": {
            ct: {
                "rows": per_type_totals[ct][0],
                "raised": per_type_totals[ct][1],
                "rate": _rate(per_type_totals[ct][1], per_type_totals[ct][0]),
            }
            for ct in CONFLICT_TYPES
        },
        "by_confidence_within_type": {ct: fmt_buckets(by_type[ct]) for ct in CONFLICT_TYPES},
        "raised_outcome": dict(Counter(_outcome(r) for r in raised_rows)),
        "raised_conflict_kind": dict(
            Counter(r.get("conflict_kind", "") or "(none)" for r in raised_rows)
        ),
        "raised_by_confidence": dict(
            Counter(_k5(agreement[r["id"]]) for r in raised_rows if r["id"] in agreement)
        ),
    }


def _plot(results: dict, conf_dist: dict, out_path: str) -> None:
    """Grouped bars: raise-rate by confidence bucket, overall (per cell) + within-C3 (star)."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    x = range(len(CONF_BUCKETS))
    width = 0.38

    # left: overall raise-rate by confidence, tiser vs base
    for i, cell in enumerate(CELLS):
        rates = [results[cell]["by_confidence"][b]["rate"] * 100 for b in CONF_BUCKETS]
        ax1.bar([xi + (i - 0.5) * width for xi in x], rates, width, label=cell)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(CONF_BUCKETS)
    ax1.set_xlabel("initial closed-book memory confidence")
    ax1.set_ylabel("conflict-raised in <reflection> (%)")
    ax1.set_title("Conflict-raise rate by memory confidence")
    ax1.legend()

    # right: within-C3 (the class that actually raises), star cell
    star = CELLS[0]
    c3 = results[star]["by_confidence_within_type"]["C3"]
    rates = [c3[b]["rate"] * 100 for b in CONF_BUCKETS]
    ax2.bar(list(x), rates, width * 1.4, color="#c44e52")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(CONF_BUCKETS)
    ax2.set_xlabel("initial closed-book memory confidence")
    ax2.set_ylabel("conflict-raised (%)")
    ax2.set_title(f"Within C3 (order-reversal), {star}")

    fig.suptitle(
        "Does memory confidence drive conflict-raising?  (no monotonic trend; peaks at 4/5)",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/conflict.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)

    # M1/M2 closed-book memory confidence per item (the eligibility gate ran on TISER).
    eligible = read_jsonl(stage_dir(cfg, "eligible") + "/eligible.jsonl")
    agreement = {r["id"]: r["agreement"] for r in eligible}
    conf_dist = dict(Counter(_k5(a) for a in agreement.values()))

    audit_dir = os.path.join(stage_dir(cfg, "scored"), "audit")
    results: dict[str, dict] = {}
    all_raised: list[dict] = []
    for cell in CELLS:
        with open(os.path.join(audit_dir, f"{cell}.audit.csv")) as f:
            rows = list(csv.DictReader(f))
        results[cell] = analyse_cell(rows, agreement)
        for r in rows:
            if _is_true(r["agent_reflection_conflict_audit"]) and r["id"] in agreement:
                all_raised.append(
                    {
                        "cell": cell,
                        "id": r["id"],
                        "conflict_type": r["conflict_type"],
                        "memory_confidence": _k5(agreement[r["id"]]),
                        "outcome": _outcome(r),
                        "faithful_em": r.get("faithful_em", ""),
                        "memorised_em": r.get("memorised_em", ""),
                        "conflict_kind": r.get("conflict_kind", ""),
                        "agent_rationale": r.get("agent_rationale", ""),
                        "reflection_text": r.get("reflection_text", ""),
                    }
                )

    out_dir = stage_dir(cfg, "confidence_vs_reflection")

    summary = {
        "question": (
            "Among conflict items whose reflection raised the context-memory conflict "
            "(LLM-agent audit), what was the model's initial closed-book memory confidence, "
            "and does raising concentrate on the most-confident (5/5) facts?"
        ),
        "verdict": (
            "No. Raise-rate is non-monotonic in confidence (peaks at 4/5, not 5/5); the "
            "real driver is conflict TYPE (order-reversal/C3). See by_confidence and "
            "by_conflict_type below."
        ),
        "primary_cell": CELLS[0],
        "eligible_confidence_distribution": conf_dist,
        "cells": results,
    }
    write_json(os.path.join(out_dir, "confidence_vs_reflection.json"), summary)

    csv_path = os.path.join(out_dir, "raised_rows.csv")
    fields = [
        "cell",
        "id",
        "conflict_type",
        "memory_confidence",
        "outcome",
        "faithful_em",
        "memorised_em",
        "conflict_kind",
        "agent_rationale",
        "reflection_text",
    ]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_raised)

    _plot(results, conf_dist, os.path.join(out_dir, "confidence_vs_reflection.png"))

    write_run_meta(
        out_dir,
        cfg,
        extra={
            "inputs": [
                "outputs/conflict/eligible/eligible.jsonl",
                *[f"outputs/conflict/scored/audit/{c}.audit.csv" for c in CELLS],
            ],
            "cells": CELLS,
        },
    )

    # Console summary
    print(f"eligible confidence distribution: {conf_dist} (total {len(agreement)})")
    for cell in CELLS:
        res = results[cell]
        tag = " (primary/star)" if cell == CELLS[0] else ""
        print(f"\n[{cell}{tag}] agent-raised {res['n_raised']}/{res['n_rows']} = {res['agent_rate_overall']:.4f}")
        print(f"  unmatched ids: {res['n_unmatched_ids']}")
        print("  raise-rate by confidence:")
        for b in CONF_BUCKETS:
            d = res["by_confidence"][b]
            print(f"    {b}: {d['raised']}/{d['rows']} = {d['rate']:.3f}")
        print("  raise-rate by conflict_type:")
        for ct in CONFLICT_TYPES:
            d = res["by_conflict_type"][ct]
            print(f"    {ct}: {d['raised']}/{d['rows']} = {d['rate']:.3f}")
        print(f"  among raised: outcome={res['raised_outcome']}  kind={res['raised_conflict_kind']}")
    print(f"\nwrote -> {out_dir}")


if __name__ == "__main__":
    main()
