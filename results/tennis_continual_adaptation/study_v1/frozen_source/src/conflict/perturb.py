"""M3 - deterministic perturbation engine (CPU, seeded).

Turns each eligible item into one labelled conflict per applicable class (D-NCLASS):

  C1 date-shift   (L2, TimeQA)      - interval-swap so a *different* value covers the
                                      queried time-point; answer(c') != m.
  C2 entity-swap  (L2, L3, TimeQA)  - replace the gold answer entity with a same-type
                                      distractor drawn from other contexts.
  C3 order-reversal (L3 only)       - re-date events so the before/after neighbour of the
                                      referenced entity flips to a different value.

Plus a no-conflict control arm (D-CTRL): a benign event-reorder that leaves answer(c') == m,
a faithfulness floor and a guard against "the edit just broke the context".

Every emitted c' is rendered through the M0 serializers and re-parsed (assert_round_trip),
so the edited context stays byte-faithful to the released template. Rows are keyed by
(id, conflict_type).

Under D-ANCHOR, m == answer_orig on the eligible set, so the conflict invariant
answer(c') != m is checked against answer_orig.

Output: 'outputs/conflict/conflicts/{conflict_set.jsonl, conflict_report.json,
conflict_sample.jsonl, run_meta.json}'.
"""

from __future__ import annotations

import copy
import os
import random
import re

from src.conflict.context_parse import (
    assert_round_trip,
    parse_context,
)
from src.conflict.io import read_jsonl, stage_dir, write_jsonl, write_run_meta
from src.eval.metrics import normalize_answer
from src.utils.io import write_json

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MONTH_IDX = {m: i for i, m in enumerate(_MONTHS)}

# Query time-anchor patterns (verified against the templated questions per split). A month,
# where present, is an optional leading month-name; endpoints may be year-only. TimeQA
# 'before/after <date>' questions are open-ended ordering queries (not closed point/interval
# coverage) and are deliberately left unmatched -> dropped from C1.
_MON = r"(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),? )?"  # optional 'Jan ' / 'Jan, '
_RE_INTERVAL = re.compile(rf"\b(?:from|between) {_MON}(\d{{3,4}}) (?:to|and) {_MON}(\d{{3,4}})")
_RE_POINT = re.compile(rf"\bin {_MON}(\d{{3,4}})")  # 'in Jan, 1948' / 'in Jun 1992' / 'in 2016'
# L3 before/after reference clause.
_RE_L3_REL = re.compile(r"\b(before|after)\b\s+(.+?)\??$")


# --------------------------------------------------------------------------- anchors

def _ordinal(month: str | None, year: int, *, upper: bool) -> int:
    """Month-resolution ordinal (year*12 + month_index). A missing month spans the whole
    year, so it resolves to Dec for an upper bound and Jan for a lower bound."""
    idx = _MONTH_IDX[month] if month else (11 if upper else 0)
    return year * 12 + idx


def derive_query_anchor(q_type: str, q: str) -> tuple[int, int] | None:
    """Return the queried (lo, hi) month-ordinal interval from a question, or None.

    Handles closed point ('in [Mon] YYYY') and closed interval ('from/between [Mon] YYYY
    to/and [Mon] YYYY', month-optional on either endpoint) queries across L2/TimeQA. A point
    has lo == hi. Open-ended 'before/after <date>' TimeQA questions are ordering queries, not
    point coverage, so they return None and the item is dropped from C1 (kept for C2).
    """
    if q_type not in ("tempreason_l2", "timeqa_easy", "timeqa_hard"):
        return None
    iv = _RE_INTERVAL.search(q)
    if iv:
        m1, y1, m2, y2 = iv.group(1), int(iv.group(2)), iv.group(3), int(iv.group(4))
        return (_ordinal(m1, y1, upper=False), _ordinal(m2, y2, upper=True))
    pt = _RE_POINT.search(q)
    if pt:
        m, y = pt.group(1), int(pt.group(2))
        return (_ordinal(m, y, upper=False), _ordinal(m, y, upper=True))
    return None


def _event_interval(e: dict) -> tuple[int, int]:
    """An event's (lo, hi) month-ordinal interval (inclusive)."""
    return (
        _ordinal(e["start_month"], e["start_year"], upper=False),
        _ordinal(e["end_month"], e["end_year"], upper=True),
    )


def _covers(e: dict, anchor: tuple[int, int]) -> bool:
    lo, hi = _event_interval(e)
    return lo <= anchor[0] and anchor[1] <= hi


# ------------------------------------------------------------------- value accessors

def _timeqa_value(e: dict) -> str:
    return " ".join(e["values"])


def extract_objects(events: list[dict], gold_idx: int, answer_orig: str) -> list[str | None]:
    """L2/L3 object per event via the gold event's answer-template hole.

    Split the gold head on 'answer_orig' into (prefix, suffix); a sibling event's object is
    the span filling the same hole. Robust to object-first relations and shared answer
    prefixes (where a longest-common-prefix split fails). Returns None per event that does
    not match the template.
    """
    gh = events[gold_idx]["head"]
    pos = gh.rfind(answer_orig)
    if pos < 0:
        return [None] * len(events)
    prefix, suffix = gh[:pos], gh[pos + len(answer_orig):]
    out: list[str | None] = []
    for e in events:
        h = e["head"]
        if h.startswith(prefix) and h.endswith(suffix) and len(h) >= len(prefix) + len(suffix):
            out.append(h[len(prefix): len(h) - len(suffix)] if suffix else h[len(prefix):])
        else:
            out.append(None)
    return out


# ------------------------------------------------------------------- gold localisation

def locate_gold_covering(item: dict) -> tuple[int, tuple[int, int]] | None:
    """L2/TimeQA: the single event covering the query anchor whose value == answer_orig.

    Returns (gold_idx, anchor) or None (anchor underivable / not single-coverage / value
    mismatch). Single-coverage is the C1 validity guard (rejects boundary-ambiguous points).
    """
    anchor = derive_query_anchor(item["q_type"], item["q"])
    if anchor is None:
        return None
    events = item["ctx_events"]
    covering = [i for i, e in enumerate(events) if _covers(e, anchor)]
    if len(covering) != 1:
        return None
    gold = covering[0]
    if not _gold_holds_answer(item, gold):
        return None
    return gold, anchor


def locate_gold_l3(item: dict) -> tuple[int, int, str] | None:
    """L3: (gold_idx, ref_idx, rel) where gold is the before/after chronological neighbour
    of the referenced entity. Returns None if the clause / reference / neighbour is not
    cleanly resolvable or the neighbour does not hold answer_orig."""
    m = _RE_L3_REL.search(item["q"])
    if not m:
        return None
    rel, ref_text = m.group(1), m.group(2).strip()
    events = item["ctx_events"]
    ref_hits = [i for i, e in enumerate(events) if ref_text in e["head"]]
    if len(ref_hits) != 1:
        return None
    ref_idx = ref_hits[0]
    order = sorted(range(len(events)), key=lambda i: _event_interval(events[i]))
    pos = {idx: p for p, idx in enumerate(order)}
    rp = pos[ref_idx]
    if rel == "before":
        neigh = order[rp - 1] if rp - 1 >= 0 else None
    else:
        neigh = order[rp + 1] if rp + 1 < len(order) else None
    if neigh is None or not _gold_holds_answer(item, neigh):
        return None
    return neigh, ref_idx, rel


def _gold_holds_answer(item: dict, idx: int) -> bool:
    e = item["ctx_events"][idx]
    if item["q_type"].startswith("tempreason"):
        return item["answer_orig"] in e["head"]
    return _timeqa_value(e) == item["answer_orig"]


# --------------------------------------------------------------------- distractor pool

def build_distractor_pools(items: list[dict]) -> dict:
    """Cross-context distractor pools (D-C2). L2/L3 entities are pooled by q_type; TimeQA
    value-sets are pooled by relation (team/spouse/school/position/…) for type-compatibility."""
    l2l3: dict[str, set[str]] = {}
    timeqa: dict[str | None, list[list[str]]] = {}
    for it in items:
        qt = it["q_type"]
        if qt.startswith("tempreason"):
            l2l3.setdefault(qt, set()).add(it["answer_orig"])
        else:
            for e in it["ctx_events"]:
                timeqa.setdefault(e["relation"], []).append(e["values"])
    return {"l2l3": {k: sorted(v) for k, v in l2l3.items()}, "timeqa": timeqa}


def _context_strings(item: dict) -> str:
    return " ".join(e["raw"] for e in item["ctx_events"])


# ------------------------------------------------------------------------- edits (C1)

def build_c1(item: dict, rng: random.Random) -> dict | str:
    """Interval-swap so a different in-context value covers the query anchor.

    Returns a conflict row, or a short drop-reason string."""
    loc = locate_gold_covering(item)
    if loc is None:
        return "anchor_unresolved_or_not_single_cover"
    gold, anchor = loc
    events = item["ctx_events"]
    if item["q_type"].startswith("tempreason"):
        objs = extract_objects(events, gold, item["answer_orig"])
    else:
        objs = [_timeqa_value(e) for e in events]
    m = item["m"]
    # Distractor event: another event whose value is known and != m.
    cands = [
        i for i, o in enumerate(objs)
        if i != gold and o is not None and normalize_answer(o) != normalize_answer(m)
    ]
    if not cands:
        return "no_distractor_value"
    d = rng.choice(cands)
    new_events = copy.deepcopy(events)
    _swap_intervals(new_events[gold], new_events[d])
    # After the swap the distractor event sits at the gold's old interval -> it must now be
    # the unique cover of the anchor (interval-swap preserves the disjoint partition).
    covering = [i for i, e in enumerate(new_events) if _covers(e, anchor)]
    if covering != [d]:
        return "post_swap_coverage_broke"
    answer_prime = objs[d]
    return _finalise(item, "C1", new_events, answer_prime,
                     {"gold_idx": gold, "distractor_idx": d, "edit": "interval_swap"})


def _swap_intervals(a: dict, b: dict) -> None:
    for k in ("start_month", "start_year", "end_month", "end_year"):
        a[k], b[k] = b[k], a[k]


# ------------------------------------------------------------------------- edits (C2)

def build_c2(item: dict, pools: dict, rng: random.Random) -> dict | str:
    """Replace the gold answer entity with a same-type distractor from another context."""
    if item["q_type"].startswith("tempreason"):
        return _build_c2_l2l3(item, pools, rng)
    return _build_c2_timeqa(item, pools, rng)


def _locate_any_gold(item: dict) -> int | None:
    """Gold-event index for C2, localised the same way as the anchor/L3 classes so all
    classes act on one canonical event."""
    if item["q_type"] == "tempreason_l3":
        loc = locate_gold_l3(item)
        return loc[0] if loc else None
    loc = locate_gold_covering(item)
    return loc[0] if loc else None


def _build_c2_l2l3(item: dict, pools: dict, rng: random.Random) -> dict | str:
    gold = _locate_any_gold(item)
    if gold is None:
        return "gold_unlocalised"
    ao, m = item["answer_orig"], item["m"]
    ctx_blob = _context_strings(item)
    pool = [
        e for e in pools["l2l3"].get(item["q_type"], [])
        if normalize_answer(e) not in (normalize_answer(ao), normalize_answer(m))
        and e not in ctx_blob
    ]
    if not pool:
        return "no_distractor_in_pool"
    distractor = rng.choice(pool)
    new_events = copy.deepcopy(item["ctx_events"])
    head = new_events[gold]["head"]
    new_head = head.replace(ao, distractor)
    if ao in new_head or distractor not in new_head:
        return "ambiguous_substitution"
    new_events[gold]["head"] = new_head
    return _finalise(item, "C2", new_events, distractor,
                     {"gold_idx": gold, "distractor": distractor, "edit": "entity_swap"})


def _build_c2_timeqa(item: dict, pools: dict, rng: random.Random) -> dict | str:
    gold = _locate_any_gold(item)
    if gold is None:
        return "gold_unlocalised"
    ao, m = item["answer_orig"], item["m"]
    relation = item["ctx_events"][gold]["relation"]
    ctx_blob = _context_strings(item)
    pool = [
        vals for vals in pools["timeqa"].get(relation, [])
        if normalize_answer(" ".join(vals)) not in (normalize_answer(ao), normalize_answer(m))
        and " ".join(vals) not in ctx_blob
    ]
    if not pool:
        return "no_distractor_in_pool"
    distractor_vals = rng.choice(pool)
    new_events = copy.deepcopy(item["ctx_events"])
    new_events[gold]["values"] = list(distractor_vals)
    answer_prime = " ".join(distractor_vals)
    return _finalise(item, "C2", new_events, answer_prime,
                     {"gold_idx": gold, "distractor": answer_prime, "edit": "entity_swap"})


# ------------------------------------------------------------------------- edits (C3)

def build_c3(item: dict, rng: random.Random) -> dict | str:
    """Re-date events so a different value becomes the before/after neighbour of the ref."""
    loc = locate_gold_l3(item)
    if loc is None:
        return "ref_or_neighbour_unresolved"
    gold, ref_idx, rel = loc
    events = item["ctx_events"]
    objs = extract_objects(events, gold, item["answer_orig"])
    m = item["m"]
    cands = [
        i for i, o in enumerate(objs)
        if i not in (gold, ref_idx) and o is not None
        and normalize_answer(o) != normalize_answer(m)
    ]
    if not cands:
        return "no_distractor_value"
    target = rng.choice(cands)
    new_events = copy.deepcopy(events)
    _swap_intervals(new_events[gold], new_events[target])
    # The target now occupies the gold's old interval -> recompute the neighbour of ref.
    order = sorted(range(len(new_events)), key=lambda i: _event_interval(new_events[i]))
    pos = {idx: p for p, idx in enumerate(order)}
    rp = pos[ref_idx]
    new_neigh = order[rp - 1] if rel == "before" and rp - 1 >= 0 else (
        order[rp + 1] if rel == "after" and rp + 1 < len(order) else None
    )
    if new_neigh != target:
        return "neighbour_swap_ineffective"
    return _finalise(item, "C3", new_events, objs[target],
                     {"gold_idx": gold, "ref_idx": ref_idx, "target_idx": target,
                      "rel": rel, "edit": "order_reversal"})


# --------------------------------------------------------------------- control (D-CTRL)

def build_control(item: dict, rng: random.Random) -> dict | str:
    """Benign event-reorder: bytes change, the answer does not (answer(c') == m).

    The answer is determined by date coverage / chronology, not text order, so shuffling the
    serialised event order leaves it unchanged - a faithfulness floor and a 'did the edit
    just break the context?' guard."""
    events = item["ctx_events"]
    if len(events) < 2:
        return "too_few_events"
    new_events = copy.deepcopy(events)
    for _ in range(8):  # ensure a real reorder
        rng.shuffle(new_events)
        if [e["raw"] for e in new_events] != [e["raw"] for e in events]:
            break
    else:
        return "reorder_noop"
    return _finalise(item, "control", new_events, item["answer_orig"], {"edit": "reorder"})


# ------------------------------------------------------------------------- finalisation

def _finalise(item: dict, conflict_type: str, new_events: list[dict],
              answer_prime: str, edit_meta: dict) -> dict | str:
    """Serialise the edited events (with a round-trip assert) and assemble the row."""
    try:
        ctx_prime = assert_round_trip(item["split"], new_events)
    except Exception:  # round-trip failure -> the edit broke the template; drop it
        return "round_trip_fail"
    m = item["m"]
    is_control = conflict_type == "control"
    conflict_holds = normalize_answer(answer_prime) != normalize_answer(m)
    validity_ok = (normalize_answer(answer_prime) == normalize_answer(m)) if is_control else conflict_holds
    return {
        "id": item["id"],
        "split": item["split"],
        "q": item["q"],
        "q_type": item["q_type"],
        "conflict_type": conflict_type,
        "ctx_prime": ctx_prime,
        "answer_ctx_prime": answer_prime,
        "m": m,
        "answer_orig": item["answer_orig"],
        "edit_meta": edit_meta,
        "validity_ok": validity_ok,
    }


# ------------------------------------------------------------------------------- driver

_BUILDERS = {"C1": "C1", "C2": "C2", "C3": "C3"}


def build_conflicts(cfg) -> dict:
    pcfg = cfg.conflict.perturb
    enabled = set(pcfg.classes)
    rng = random.Random(cfg.seed)

    items = read_jsonl(os.path.join(stage_dir(cfg, "eligible"), "eligible.jsonl"))
    pools = build_distractor_pools(items)

    rows: list[dict] = []
    drops: dict[str, dict[str, int]] = {}  # class -> {reason: count}
    for it in items:
        applicable = set(it["applicable_classes"]) & enabled
        for cls in sorted(applicable):
            if cls == "C1":
                row = build_c1(it, rng)
            elif cls == "C2":
                row = build_c2(it, pools, rng)
            elif cls == "C3":
                row = build_c3(it, rng)
            else:
                row = "class_not_implemented"
            if isinstance(row, str):
                reasons = drops.setdefault(cls, {})
                reasons[row] = reasons.get(row, 0) + 1
            else:
                rows.append(row)

    # Control arm (D-CTRL): a seeded sample of eligible items, benign-edited.
    control_rows = _build_control_arm(items, pcfg.control_size, rng)
    rows.extend(control_rows)

    out_dir = stage_dir(cfg, "conflicts")
    write_jsonl(os.path.join(out_dir, "conflict_set.jsonl"), rows)
    sample = rng.sample(rows, min(30, len(rows)))
    write_jsonl(os.path.join(out_dir, "conflict_sample.jsonl"), sample)
    report = _report(rows, drops, len(items), enabled)
    write_json(os.path.join(out_dir, "conflict_report.json"), report)
    write_run_meta(out_dir, cfg, extra={"classes": sorted(enabled), "control_size": pcfg.control_size})

    print(f"[M3] built {len(rows)} conflict rows from {len(items)} eligible items -> {out_dir}")
    print(f"[M3] per class: {report['per_class']}")
    print(f"[M3] validity pass-rate: {report['validity_pass_rate']}")
    print(f"[M3] drops per class: { {c: sum(v.values()) for c, v in drops.items()} }")
    return report


def _build_control_arm(items: list[dict], control_size: int, rng: random.Random) -> list[dict]:
    pool = [it for it in items if len(it["ctx_events"]) >= 2]
    rng.shuffle(pool)
    out: list[dict] = []
    for it in pool:
        if len(out) >= control_size:
            break
        row = build_control(it, rng)
        if row is not None:
            out.append(row)
    return out


def _report(rows, drops, n_items, enabled) -> dict:
    per_class: dict[str, int] = {}
    valid_per_class: dict[str, int] = {}
    for r in rows:
        c = r["conflict_type"]
        per_class[c] = per_class.get(c, 0) + 1
        valid_per_class[c] = valid_per_class.get(c, 0) + int(r["validity_ok"])
    pass_rate = {
        c: round(valid_per_class[c] / per_class[c], 4) if per_class[c] else 0.0
        for c in per_class
    }
    return {
        "n_eligible_items": n_items,
        "enabled_classes": sorted(enabled),
        "n_rows": len(rows),
        "per_class": dict(sorted(per_class.items())),
        "valid_per_class": dict(sorted(valid_per_class.items())),
        "validity_pass_rate": dict(sorted(pass_rate.items())),
        "dropped_per_class": {c: sum(v.values()) for c, v in sorted(drops.items())},
        "drop_reasons": {c: dict(sorted(v.items())) for c, v in sorted(drops.items())},
        "control_size": per_class.get("control", 0),
    }
