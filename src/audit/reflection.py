"""Shared rubric, validation, and summaries for reflection judging."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any


PROMPT_VERSION = "reflection-explicit-conflict-v1"
LABELS = {"explicit_conflict", "no_explicit_conflict", "unscorable"}
MENTION_KINDS = {
    "memory_context_mismatch",
    "contradiction_or_inconsistency",
    "uncertainty_or_doubt",
    "other",
    "none",
}

PASS_PROMPTS = {
    "judge_a": """You are auditing only the text inside a model's <reflection> field.
Label explicit_conflict only when the reflection itself explicitly acknowledges a
mismatch, contradiction, inconsistency, or doubt between the supplied context and
prior knowledge, memory, familiarity, or an alternative factual answer.

Do not infer a conflict from outside information. Merely rechecking a timeline,
saying the reasoning is correct, correcting an arithmetic step, or mentioning an
error without contrasting context with prior knowledge is no_explicit_conflict.
Use unscorable only when the reflection is empty or too malformed to interpret.
For explicit_conflict, copy a short exact substring as evidence_quote. Otherwise
return an empty evidence_quote. Keep the rationale to one sentence.""",
    "judge_b": """Apply a conservative falsification test to one reflection.
The positive label explicit_conflict requires words in the reflection that clearly
recognise tension between context-provided evidence and something remembered,
generally known, expected, or otherwise believed. The existence of an experimental
conflict is not evidence: judge only what the reflection says.

Routine self-verification, agreement with a timeline, or 'no errors' language is
no_explicit_conflict. Use unscorable only for empty or uninterpretable text. A
positive evidence_quote must be copied exactly from the reflection; non-positive
labels require an empty quote. Give one concise sentence of rationale.""",
}

ADJUDICATOR_PROMPT = """Adjudicate two labels for the same reflection using the
same conservative rule: explicit_conflict requires an explicit textual
acknowledgement of tension between supplied context and prior knowledge, memory,
expectation, or an alternative factual answer. Judge only the reflection. Routine
self-checking is negative. Copy an exact evidence substring only for a positive
label; otherwise use an empty quote. Return the best final label and one concise
sentence of rationale."""

JUDGMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": sorted(LABELS)},
        "mention_kind": {"type": "string", "enum": sorted(MENTION_KINDS)},
        "evidence_quote": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["label", "mention_kind", "evidence_quote", "rationale"],
    "additionalProperties": False,
}


def validate_judgment(value: dict[str, Any], reflection: str) -> None:
    if value.get("label") not in LABELS:
        raise ValueError(f"invalid label: {value.get('label')!r}")
    if value.get("mention_kind") not in MENTION_KINDS:
        raise ValueError(f"invalid mention_kind: {value.get('mention_kind')!r}")
    quote = value.get("evidence_quote")
    rationale = value.get("rationale")
    if not isinstance(quote, str) or not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("evidence_quote and non-empty rationale must be strings")
    if value["label"] == "explicit_conflict":
        if not quote or quote not in reflection:
            raise ValueError("positive evidence_quote must be an exact reflection substring")
    elif quote:
        raise ValueError("non-positive judgment must use an empty evidence_quote")


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scorable = [row for row in rows if row["final_label"] != "unscorable"]
    genuine = [row for row in scorable if row["conflict_type"] != "control"]
    controls = [row for row in scorable if row["conflict_type"] == "control"]
    def positives(values: list[dict[str, Any]]) -> int:
        return sum(row["final_label"] == "explicit_conflict" for row in values)

    faithful = [row for row in genuine if float(row.get("faithful_em") or 0) == 1.0]
    silent = sum(row["final_label"] != "explicit_conflict" for row in faithful)
    disagreement = sum(
        bool(row["judge_a_label"])
        and bool(row["judge_b_label"])
        and row["judge_a_label"] != row["judge_b_label"]
        for row in scorable
    )
    per_class = {}
    for conflict_type in sorted({row["conflict_type"] for row in scorable}):
        subset = [row for row in scorable if row["conflict_type"] == conflict_type]
        per_class[conflict_type] = _rate_record(positives(subset), len(subset))
    return {
        "all_rows": len(rows),
        "unscorable": len(rows) - len(scorable),
        "genuine_conflicts": _rate_record(positives(genuine), len(genuine)),
        "controls_false_positive": _rate_record(positives(controls), len(controls)),
        "two_pass_disagreement": _rate_record(disagreement, len(scorable)),
        "silent_override_among_faithful": _rate_record(silent, len(faithful)),
        "per_class": per_class,
        "lexical_vs_judge": _lexical_confusion(scorable),
    }


def _rate_record(count: int, n: int) -> dict[str, Any]:
    low, high = _wilson_interval(count, n)
    return {
        "count": count,
        "n": n,
        "rate": count / n if n else None,
        "wilson_95": [low, high],
    }


def _wilson_interval(
    count: int, n: int, z: float = 1.959963984540054
) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    p = count / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return centre - radius, centre + radius


def _lexical_confusion(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        lexical = bool(row.get("reflection_mentions_conflict"))
        judged = row["final_label"] == "explicit_conflict"
        counts[(lexical, judged)] += 1
    return {
        "true_positive": counts[(True, True)],
        "false_positive": counts[(True, False)],
        "false_negative": counts[(False, True)],
        "true_negative": counts[(False, False)],
    }
