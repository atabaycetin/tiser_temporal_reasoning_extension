"""Paired metrics; original-TISER macro is always stratified over five splits."""
from __future__ import annotations

import math
import os
from pathlib import Path

from src.experiment.artifacts import digest, identity, jsonl, read, sha256, validate_rows, write

MACRO_SPLITS = ("tgqa_test", "tempreason_l2_test", "tempreason_l3_test", "timeqa_easy_test", "timeqa_hard_test")


def forgetting_gate(interval, margin=0.02):
    low, high = interval
    if not (-1 <= low <= high <= 1):
        raise ValueError("Invalid EM-delta interval")
    return "clear_forgetting" if high < -margin else ("non_inferior" if low > -margin else "inconclusive")


def token_gate(reference, replay, threshold=0.10):
    if reference <= 0 or replay <= 0:
        raise ValueError("Token totals must be positive")
    ratio = replay / reference
    return {"reference_supervised_tokens": reference, "replay_supervised_tokens": replay,
            "relative_difference": ratio - 1, "threshold": threshold,
            "sensitivity_required": abs(replay - reference) > threshold * reference}


def holm(pvalues):
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in pvalues):
        raise ValueError("Invalid p-value")
    ordered = sorted(range(len(pvalues)), key=pvalues.__getitem__)
    result, bound = [0.0] * len(pvalues), 0.0
    for rank, i in enumerate(ordered):
        bound = max(bound, min(1.0, (len(pvalues) - rank) * pvalues[i]))
        result[i] = bound
    return result


def mcnemar(a, b):
    counts = {"both_correct": 0, "baseline_only": 0, "candidate_only": 0, "both_wrong": 0}
    for x, y in zip(a, b):
        key = "both_correct" if x and y else "baseline_only" if x else "candidate_only" if y else "both_wrong"
        counts[key] += 1
    n = counts["baseline_only"] + counts["candidate_only"]
    k = min(counts["baseline_only"], counts["candidate_only"])
    if n == 0:
        p = 1.0
    else:
        logs = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) - n * math.log(2) for i in range(k + 1)]
        peak = max(logs)
        p = min(1.0, 2 * math.exp(peak) * math.fsum(math.exp(v - peak) for v in logs))
    return {**counts, "p_exact_two_sided": p}


def paired_rows(baseline, candidate):
    a_ids, b_ids = validate_rows(baseline, "gold"), validate_rows(candidate, "gold")
    if a_ids != b_ids or [r["gold"] for r in baseline] != [r["gold"] for r in candidate]:
        raise ValueError("Paired prediction ID/order/gold mismatch")
    if [r.get("scoring_view_sha256") for r in baseline] != [r.get("scoring_view_sha256") for r in candidate]:
        raise ValueError("Paired scoring views differ")
    for r in [*baseline, *candidate]:
        if r.get("em") not in (0, 1) or not isinstance(r.get("f1"), (int, float)) or not 0 <= r["f1"] <= 1:
            raise ValueError("Invalid EM/F1 value")


def compare(baseline, candidate, *, domain, replicates=10000, seed=42):
    import numpy as np
    paired_rows(baseline, candidate)
    if replicates < 1 or domain not in {"tennis", "tiser"}:
        raise ValueError("Invalid domain or replicate count")
    names = list(MACRO_SPLITS) if domain == "tiser" else ["tennis_temporal"]
    if not set(names) <= {r["dataset_name"] for r in baseline}:
        raise ValueError("Missing required benchmark split")
    rng = np.random.default_rng(seed)
    deltas = np.zeros((replicates, 2))
    per_split, tests = {}, {}
    for name in names:
        indices = [i for i, r in enumerate(baseline) if r["dataset_name"] == name]
        a = np.array([[baseline[i][m] for m in ("em", "f1")] for i in indices], dtype=float)
        b = np.array([[candidate[i][m] for m in ("em", "f1")] for i in indices], dtype=float)
        difference = b - a
        # Bounded memory on the full original-TISER complement.
        for start in range(0, replicates, 100):
            count = min(100, replicates - start)
            draws = rng.integers(0, len(indices), size=(count, len(indices)))
            deltas[start:start + count] += difference[draws].mean(axis=1) / len(names)
        per_split[name] = {"n": len(indices), "baseline": dict(zip(("em", "f1"), a.mean(axis=0).tolist())),
                           "candidate": dict(zip(("em", "f1"), b.mean(axis=0).tolist()))}
        tests[name] = mcnemar(a[:, 0].astype(bool), b[:, 0].astype(bool))
    summary = {"domain": domain, "seed": seed, "replicates": replicates, "macro_splits": names,
               "n": sum(v["n"] for v in per_split.values()), "per_split": per_split,
               "mcnemar": tests, "excluded_ood_splits": sorted({r["dataset_name"] for r in baseline} - set(names))}
    for j, metric in enumerate(("em", "f1")):
        a = sum(p["baseline"][metric] for p in per_split.values()) / len(names)
        b = sum(p["candidate"][metric] for p in per_split.values()) / len(names)
        interval = np.quantile(deltas[:, j], [0.025, 0.975]).tolist()
        summary[metric] = {"baseline": a, "candidate": b, "delta": b - a,
                           "ci95": interval, "retention_ratio": b / a if a else None}
    summary["decision"] = forgetting_gate(summary["em"]["ci95"]) if domain == "tiser" else {
        "non_inferior": summary["em"]["ci95"][0] > -0.02, "margin": 0.02}
    return summary, deltas


def analyze_spec(spec_path, output):
    import numpy as np
    spec, output = read(spec_path), Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Statistics output already exists: {output}")
    comparisons = spec["comparisons"]
    if not comparisons:
        raise ValueError("At least one preregistered comparison is required")
    ids = [c["id"] for c in comparisons]
    if len(set(ids)) != len(ids) or any(not i or Path(i).name != i for i in ids):
        raise ValueError("Comparison IDs must be unique simple filenames")
    for comparison in comparisons:
        if set(comparison) != {"id", "domain", "baseline", "candidate"}:
            raise ValueError("Comparison fields differ from the frozen schema")
    results, replicates, tests = {}, {}, []
    for c in comparisons:
        result, draws = compare(jsonl(c["baseline"]), jsonl(c["candidate"]), domain=c["domain"],
                                replicates=spec.get("replicates", 10000), seed=spec.get("seed", 42))
        result["inputs"] = {k: {"path": c[k], "sha256": sha256(c[k])} for k in ("baseline", "candidate")}
        results[c["id"]], replicates[c["id"]] = result, draws
        for split, table in result["mcnemar"].items():
            tests.append((c["id"], split, table["p_exact_two_sided"]))
    for (cid, split, _), p in zip(tests, holm([t[2] for t in tests])):
        results[cid]["mcnemar"][split]["p_holm"] = p
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(output.name + f".{os.getpid()}.tmp")
    if staging.exists():
        raise FileExistsError(f"Statistics staging path already exists: {staging}")
    staging.mkdir()
    for cid, draws in replicates.items():
        np.savez_compressed(staging / f"{cid}.bootstrap.npz", deltas=draws)
    result = {"spec_sha256": sha256(spec_path), "spec": spec, "comparisons": results,
              "holm_family": [{"comparison": c, "split": s} for c, s, _ in tests],
              "training_seeds": 1, "training_variability_measured": False}
    write(staging / "statistics.json", result)
    os.replace(staging, output)
    return result
