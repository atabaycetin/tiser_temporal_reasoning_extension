from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParseResult:
    answer: str
    malformed: bool


def _parse_tag(text: str, tag: str) -> ParseResult:
    """Extract the content of an XML-ish tag from a (possibly malformed) generation.

    Real outputs may repeat the template, drop the closing tag, or omit the tag entirely.
    Prefer the last well-formed '<tag>...</tag>' block; otherwise take everything after the
    last opening tag (flagged malformed); otherwise return empty (flagged malformed). The
    'answer' field carries the extracted text regardless of tag. Never raises.
    """
    block = re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL | re.IGNORECASE)
    open_re = re.compile(rf"<{tag}>(.*)", re.DOTALL | re.IGNORECASE)

    blocks = block.findall(text)
    if blocks:
        return ParseResult(answer=blocks[-1].strip(), malformed=False)

    open_match = None
    for open_match in open_re.finditer(text):
        pass
    if open_match is not None:
        return ParseResult(answer=open_match.group(1).strip(), malformed=True)

    return ParseResult(answer="", malformed=True)


def parse_answer(text: str) -> ParseResult:
    """Extract the <answer> content from a (possibly malformed) generation."""
    return _parse_tag(text, "answer")


def parse_plain(text: str) -> ParseResult:
    """Treat the whole completion as the answer (non-tagged 'standard'-prompt cells).

    The standard prompt (D-STD) asks for a short, direct answer after '### Answer:' and
    emits no <answer> tag, so the raw completion *is* the answer; malformed only if empty.
    Scoring normalises before matching, so surrounding whitespace is irrelevant."""
    stripped = text.strip()
    return ParseResult(answer=stripped, malformed=not stripped)


def parse_reflection(text: str) -> ParseResult:
    """Extract the <reflection> content (the TISER audit step). Mirrors 'parse_answer'."""
    return _parse_tag(text, "reflection")


def parse_timeline(text: str) -> ParseResult:
    """Extract the <timeline> content (the TISER timeline step). Mirrors 'parse_answer'."""
    return _parse_tag(text, "timeline")
