"""M2 - eligibility filter + YIELD GATE.

Joins the subset (M0) with the primary model's closed-book memory (M1) and keeps
the items that form a clean memory<->context collision:

  D-ELIG (strict): keep iff  agreement >= agreement_min  AND  EM(m, answer_orig) == 1
                   (confident AND correct -> m == gold on the kept set, D-ANCHOR).

Items that are confident-but-wrong (m != gold) are persisted as a flagged bucket,
not discarded (D-ELIG). The yield report counts eligible items per split / q_type /
applicable conflict-class and emits the GO/NO-GO verdict against the per-class target
(D-CLASSN) -- the milestone that gates whether the downstream build (M3/M4) proceeds.

Output: 'outputs/conflict/eligible/{eligible.jsonl, confident_wrong.jsonl, yield_report.json}'.
CPU stage.
"""

from __future__ import annotations

import os

from src.conflict.io import read_jsonl, stage_dir, write_jsonl, write_run_meta
from src.eval.metrics import exact_match, normalize_answer
from src.utils.io import write_json


def _load_memory(cfg, tag: str) -> dict[str, dict]:
    path = os.path.join(stage_dir(cfg, "memory"), f"memory_{tag}.jsonl")
    if not os.path.exists(path):
        raise FileNotFoundError(f"missing memory artifact for tag {tag!r}: {path} (run M1 first)")
    return {r["id"]: r for r in read_jsonl(path)}


def filter_eligible(cfg) -> dict:
    elig_cfg = cfg.conflict.eligibility
    agreement_min = elig_cfg.agreement_min
    primary = elig_cfg.primary_model

    items = read_jsonl(os.path.join(stage_dir(cfg, "subset"), "items.jsonl"))
    mem = _load_memory(cfg, primary)

    eligible: list[dict] = []
    confident_wrong: list[dict] = []
    n_no_memory = 0
    for it in items:
        rec = mem.get(it["id"])
        if rec is None:
            n_no_memory += 1
            continue
        m, agreement = rec["m"], rec["agreement"]
        # An empty majority answer means no usable belief (e.g. closed-book is OOD for
        # the fine-tune and the samples were malformed) -> not confident, so it is
        # dropped rather than mis-filed into the confident-wrong bucket.
        confident = agreement >= agreement_min and bool(normalize_answer(m))
        correct = exact_match(m, it["answer_orig"]) == 1.0
        if confident and correct:
            eligible.append({**it, "m": m, "agreement": agreement, "n_malformed": rec["n_malformed"]})
        elif confident and not correct:
            confident_wrong.append(
                {"id": it["id"], "split": it["split"], "q": it["q"],
                 "answer_orig": it["answer_orig"], "m": m, "agreement": agreement}
            )

    out_dir = stage_dir(cfg, "eligible")
    write_jsonl(os.path.join(out_dir, "eligible.jsonl"), eligible)
    write_jsonl(os.path.join(out_dir, "confident_wrong.jsonl"), confident_wrong)
    report = _yield_report(cfg, eligible, confident_wrong, n_no_memory, len(items))
    report["cross_model_agreement"] = _cross_model_agreement(cfg, primary)
    write_json(os.path.join(out_dir, "yield_report.json"), report)
    write_run_meta(out_dir, cfg, extra={"primary_model": primary, "agreement_min": agreement_min})

    print(f"[M2] eligible {len(eligible)}/{len(items)} | confident-wrong {len(confident_wrong)} "
          f"| no-memory {n_no_memory}")
    print(f"[M2] eligible per class: {report['eligible_per_class']}")
    print(f"[M2] GO/NO-GO: {report['verdict']['overall']}  ({report['verdict']['per_class']})")
    return report


def _yield_report(cfg, eligible, confident_wrong, n_no_memory, n_items) -> dict:
    target = cfg.conflict.eligibility.target_n_per_class
    secondary = set(cfg.conflict.eligibility.secondary_classes)

    per_split: dict[str, int] = {}
    per_qtype: dict[str, int] = {}
    per_class: dict[str, int] = {}
    for it in eligible:
        per_split[it["split"]] = per_split.get(it["split"], 0) + 1
        per_qtype[it["q_type"]] = per_qtype.get(it["q_type"], 0) + 1
        for c in it["applicable_classes"]:
            per_class[c] = per_class.get(c, 0) + 1

    per_class_verdict = {
        c: {
            "n": per_class.get(c, 0),
            "target": target,
            "secondary": c in secondary,
            "meets_target": per_class.get(c, 0) >= target,
        }
        for c in sorted(set(per_class) | secondary | {"C1", "C2", "C3"})
    }
    # GO iff every non-secondary class that has any substrate meets the target.
    blocking = [c for c, v in per_class_verdict.items() if not v["secondary"]]
    overall = "GO" if all(per_class_verdict[c]["meets_target"] for c in blocking) else "NO-GO"

    return {
        "n_items": n_items,
        "n_eligible": len(eligible),
        "n_confident_wrong": len(confident_wrong),
        "n_no_memory": n_no_memory,
        "eligible_per_split": dict(sorted(per_split.items())),
        "eligible_per_qtype": dict(sorted(per_qtype.items())),
        "eligible_per_class": dict(sorted(per_class.items())),
        "verdict": {"overall": overall, "per_class": per_class_verdict},
    }


def _cross_model_agreement(cfg, primary: str) -> dict:
    """Fraction of shared ids where the non-primary models' m matches primary's m."""
    mem_primary = _load_memory(cfg, primary)
    out = {}
    for entry in cfg.conflict.memory.models:
        tag = entry["tag"]
        if tag == primary:
            continue
        path = os.path.join(stage_dir(cfg, "memory"), f"memory_{tag}.jsonl")
        if not os.path.exists(path):
            continue
        other = {r["id"]: r for r in read_jsonl(path)}
        shared = set(mem_primary) & set(other)
        if not shared:
            continue
        match = sum(
            normalize_answer(mem_primary[i]["m"]) == normalize_answer(other[i]["m"]) for i in shared
        )
        out[tag] = {"n_shared": len(shared), "m_agreement": match / len(shared)}
    return out
