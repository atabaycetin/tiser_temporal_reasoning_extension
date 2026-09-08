from __future__ import annotations

import re
import string
from collections import Counter

_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = str.maketrans("", "", string.punctuation)


def normalize_answer(s: str) -> str:
    """SQuAD-style normalization: lowercase, drop punctuation, drop articles, collapse whitespace."""
    s = s.lower()
    s = s.translate(_PUNCT)
    s = _ARTICLES.sub(" ", s)
    return " ".join(s.split())


def exact_match(pred: str, gold: str) -> float:
    return float(normalize_answer(pred) == normalize_answer(gold))


def token_f1(pred: str, gold: str) -> float:
    pred_tokens = normalize_answer(pred).split()
    gold_tokens = normalize_answer(gold).split()

    if not pred_tokens or not gold_tokens:
        # Both empty -> they agree; exactly one empty -> no overlap.
        return float(pred_tokens == gold_tokens)

    overlap = sum((Counter(pred_tokens) & Counter(gold_tokens)).values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def aggregate(records: list[dict], macro_splits: list[str] | None = None) -> dict:
    """Group per-example {dataset_name, em, f1} by split; macro = unweighted split mean.

    per_split is reported for every split present (informational), but the macro
    is averaged only over macro_splits (the in-domain whitelist). This keeps any
    OOD split present in the test file (e.g. tot_semantic_test) out of the headline
    number. If macro_splits is None, every present split counts.
    """
    per_split: dict[str, dict] = {}
    for name in sorted({r["dataset_name"] for r in records}):
        rows = [r for r in records if r["dataset_name"] == name]
        per_split[name] = {
            "em": sum(r["em"] for r in rows) / len(rows),
            "f1": sum(r["f1"] for r in rows) / len(rows),
            "n": len(rows),
        }

    if macro_splits is None:
        keys = list(per_split)
    else:
        keys = [s for s in macro_splits if s in per_split]

    return {
        "per_split": per_split,
        "macro_splits": keys,
        "macro_em": sum(per_split[s]["em"] for s in keys) / len(keys) if keys else 0.0,
        "macro_f1": sum(per_split[s]["f1"] for s in keys) / len(keys) if keys else 0.0,
        "n_total": len(records),
    }
