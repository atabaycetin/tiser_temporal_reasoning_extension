"""M6 - parse traces and score faithfulness (CPU).

Joins a generation file (M5) with the conflict set (M3) on (id, conflict_type) and scores,
per row:

  context-faithfulness  answer ~= answer_ctx_prime   (does it trust the edited text?)
  memorisation          answer ~= m                  (does it fall back on its belief?)
  guardrail EM          answer ~= answer_orig         (sanity; on control == faithfulness floor)

For tiser-style cells it also extracts <reflection>/<timeline> and a *lexical* conflict-mention
proxy (does the reflection use clash language?). Authoritative conflict-detection and
silent-override are M7 (out of scope) - this stage emits the reflection text they consume.

Metrics are stratified by conflict_type (incl. the control arm) in metrics.json.

Output: 'outputs/conflict/scored/<model>__<style>.jsonl' + 'scored/<model>__<style>.metrics.json'.
"""

from __future__ import annotations

import os

from src.conflict.io import read_jsonl, stage_dir, write_run_meta, write_jsonl
from src.inference.parser import parse_answer, parse_plain, parse_reflection, parse_timeline
from src.eval.metrics import exact_match, token_f1
from src.utils.io import write_json


def _mentions_conflict(reflection: str, lexicon: list[str]) -> bool:
    low = reflection.lower()
    return any(term.lower() in low for term in lexicon)


def score(cfg, model_tag: str, style: str) -> dict:
    lexicon = list(cfg.conflict.score.conflict_lexicon)
    is_tiser = style == "tiser"

    gen_path = os.path.join(stage_dir(cfg, "generations"), f"{model_tag}__{style}.jsonl")
    if not os.path.exists(gen_path):
        raise FileNotFoundError(f"missing generations: {gen_path} (run M5 first)")
    gens = read_jsonl(gen_path)

    conflicts = {
        (r["id"], r["conflict_type"]): r
        for r in read_jsonl(os.path.join(stage_dir(cfg, "conflicts"), "conflict_set.jsonl"))
    }

    scored: list[dict] = []
    for g in gens:
        key = (g["id"], g["conflict_type"])
        c = conflicts.get(key)
        if c is None:
            continue  # generation without a matching conflict row (should not happen post-join)
        raw = g["raw_generation"]
        # tiser-style emits a 4-tag trace (<answer>…</answer>); standard-style emits a bare
        # direct answer with no tags, so the whole completion is the answer.
        ans = parse_answer(raw) if is_tiser else parse_plain(raw)
        ctx_prime, m, ao = c["answer_ctx_prime"], c["m"], c["answer_orig"]

        row = {
            "id": g["id"],
            "conflict_type": g["conflict_type"],
            "model": model_tag,
            "style": style,
            "answer": ans.answer,
            "malformed": ans.malformed,
            "answer_ctx_prime": ctx_prime,
            "m": m,
            "answer_orig": ao,
            "faithful_em": exact_match(ans.answer, ctx_prime),
            "faithful_f1": token_f1(ans.answer, ctx_prime),
            "memorised_em": exact_match(ans.answer, m),
            "memorised_f1": token_f1(ans.answer, m),
            "guardrail_em": exact_match(ans.answer, ao),
        }
        if is_tiser:
            refl = parse_reflection(raw)
            row["reflection_text"] = refl.answer
            row["reflection_malformed"] = refl.malformed
            row["timeline_text"] = parse_timeline(raw).answer
            row["reflection_mentions_conflict"] = _mentions_conflict(refl.answer, lexicon)
        scored.append(row)

    out_dir = stage_dir(cfg, "scored")
    write_jsonl(os.path.join(out_dir, f"{model_tag}__{style}.jsonl"), scored)
    metrics = _metrics(scored, model_tag, style, is_tiser)
    write_json(os.path.join(out_dir, f"{model_tag}__{style}.metrics.json"), metrics)
    write_run_meta(out_dir, cfg, extra={"model_tag": model_tag, "style": style})

    o = metrics["overall"]
    print(f"[M6:{model_tag}__{style}] n={o['n']} faithful_em={o['faithful_em']:.3f} "
          f"memorised_em={o['memorised_em']:.3f} malformed_rate={o['malformed_rate']:.3f}"
          + (f" reflection_mention_rate={o['reflection_mention_rate']:.3f}" if is_tiser else ""))
    return metrics


def _agg(rows: list[dict], is_tiser: bool) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    out = {
        "n": n,
        "faithful_em": sum(r["faithful_em"] for r in rows) / n,
        "faithful_f1": sum(r["faithful_f1"] for r in rows) / n,
        "memorised_em": sum(r["memorised_em"] for r in rows) / n,
        "memorised_f1": sum(r["memorised_f1"] for r in rows) / n,
        "guardrail_em": sum(r["guardrail_em"] for r in rows) / n,
        "malformed_rate": sum(r["malformed"] for r in rows) / n,
    }
    if is_tiser:
        out["reflection_mention_rate"] = sum(r["reflection_mentions_conflict"] for r in rows) / n
    return out


def _metrics(scored: list[dict], model_tag: str, style: str, is_tiser: bool) -> dict:
    by_class: dict[str, list[dict]] = {}
    for r in scored:
        by_class.setdefault(r["conflict_type"], []).append(r)
    return {
        "model_tag": model_tag,
        "style": style,
        "overall": _agg(scored, is_tiser),
        "per_class": {c: _agg(rows, is_tiser) for c, rows in sorted(by_class.items())},
    }
