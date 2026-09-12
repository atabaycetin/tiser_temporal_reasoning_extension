"""Answer normalization helpers for tennis temporal QA."""

from __future__ import annotations

import re
import string
import unicodedata
from collections import Counter
from decimal import Decimal, InvalidOperation
from typing import Any

_ARTICLES = re.compile(r"\b(a|an|the)\b")
_RANKING_PATTERNS = (
    re.compile(r"\bworld\s+(?:no\.?|number)\s*#?\s*(\d+)\b"),
    re.compile(r"\b(?:no\.?|number)\s*#?\s*(\d+)\b"),
    re.compile(r"#\s*(\d+)\b"),
)
_NUMERIC_MINUTES = re.compile(r"\b(\d+(?:\.\d+)?)\s+minutes?\b")
_DURATION_MINUTES_ANSWER = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(?:minutes?)?\s*$",
    flags=re.IGNORECASE,
)

_APOSTROPHES = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u2032": "'",
    "\u02bc": "'",
    "\uff07": "'",
}
_DASHES = {
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2212": "-",
    "\ufe58": "-",
    "\ufe63": "-",
    "\uff0d": "-",
}

_PUNCTUATION_TO_SPACE = str.maketrans(
    {char: " " for char in string.punctuation if char not in {"'"}}
)


def _replace_unicode_variants(text: str) -> str:
    for source, target in _APOSTROPHES.items():
        text = text.replace(source, target)
    for source, target in _DASHES.items():
        text = text.replace(source, target)
    return text


def _normalize_rankings(text: str) -> str:
    for pattern in _RANKING_PATTERNS:
        text = pattern.sub(r"\1", text)
    return text


def normalize_tennis_answer(text: str) -> str:
    """Normalize tennis answer strings for deterministic EM/F1 scoring.

    This intentionally keeps name tokens intact apart from case, Unicode width,
    apostrophe, dash, punctuation, and article cleanup. It does not perform
    player aliasing or fuzzy matching.
    """
    if text is None:
        text = ""

    normalized = unicodedata.normalize("NFKC", str(text))
    normalized = _replace_unicode_variants(normalized)
    normalized = normalized.casefold()
    normalized = _normalize_rankings(normalized)
    normalized = _NUMERIC_MINUTES.sub(r"\1 minute", normalized)

    # Drop apostrophes without splitting names; turn other punctuation into
    # spaces so hyphenated names and score-like strings remain token comparable.
    normalized = normalized.replace("'", "")
    normalized = normalized.translate(_PUNCTUATION_TO_SPACE)
    normalized = _ARTICLES.sub(" ", normalized)
    normalized = _normalize_rankings(normalized)
    normalized = _NUMERIC_MINUTES.sub(r"\1 minute", normalized)

    return " ".join(normalized.split())


def is_duration_minutes_category(
    category: Any = None,
    tags: list[Any] | tuple[Any, ...] | None = None,
) -> bool:
    values = []
    if category is not None:
        values.append(str(category))
    if tags is not None:
        values.extend(str(tag) for tag in tags if tag is not None)
    return any("duration_minutes" in value.casefold() for value in values)


def canonical_duration_minutes_answer(text: str) -> str | None:
    """Return a bare numeric minute answer when the whole answer is a duration."""
    match = _DURATION_MINUTES_ANSWER.match("" if text is None else str(text))
    if not match:
        return None
    value = match.group(1)
    try:
        decimal = Decimal(value)
    except InvalidOperation:
        return value
    normalized = decimal.normalize()
    return format(normalized, "f")


def normalize_tennis_answer_for_category(
    text: str,
    *,
    category: Any = None,
    tags: list[Any] | tuple[Any, ...] | None = None,
) -> str:
    """Normalize with category-specific equivalences used only by tennis eval."""
    if is_duration_minutes_category(category, tags):
        duration = canonical_duration_minutes_answer(text)
        if duration is not None:
            return duration
    return normalize_tennis_answer(text)


def tennis_exact_match(pred: str, gold: str) -> int:
    """Return 1 when normalized prediction and gold answers are identical."""
    return int(normalize_tennis_answer(pred) == normalize_tennis_answer(gold))


def tennis_exact_match_for_category(
    pred: str,
    gold: str,
    *,
    category: Any = None,
    tags: list[Any] | tuple[Any, ...] | None = None,
) -> int:
    return int(
        normalize_tennis_answer_for_category(pred, category=category, tags=tags)
        == normalize_tennis_answer_for_category(gold, category=category, tags=tags)
    )


def tennis_token_f1(pred: str, gold: str) -> float:
    """Token-level F1 over tennis-normalized answer strings."""
    pred_tokens = normalize_tennis_answer(pred).split()
    gold_tokens = normalize_tennis_answer(gold).split()
    return _token_f1(pred_tokens, gold_tokens)


def tennis_token_f1_for_category(
    pred: str,
    gold: str,
    *,
    category: Any = None,
    tags: list[Any] | tuple[Any, ...] | None = None,
) -> float:
    pred_tokens = normalize_tennis_answer_for_category(
        pred, category=category, tags=tags
    ).split()
    gold_tokens = normalize_tennis_answer_for_category(
        gold, category=category, tags=tags
    ).split()
    return _token_f1(pred_tokens, gold_tokens)


def _token_f1(pred_tokens: list[str], gold_tokens: list[str]) -> float:
    if not pred_tokens or not gold_tokens:
        return float(pred_tokens == gold_tokens)

    overlap = sum((Counter(pred_tokens) & Counter(gold_tokens)).values())
    if overlap == 0:
        return 0.0

    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)
