"""Deterministic parsers over the TISER prompt/context (M0).

The released prompts have a fixed shape (verified to isolate 100% across all 22k
records): a fixed 4-tag instruction preamble, then 'Question: <q>', then
'Temporal context: <c>', then '### Answer:'. The two in-scope context families use
distinct verbatim templates, so structure-parsing is pure string work:

  TempReason L2/L3:  '<Entity> works for <ORG> from <Mon>, <YYYY> to <Mon>, <YYYY>.'  (xN, joined by ". ")
  TimeQA easy/hard:  '<YYYY> - <YYYY> : <Entity>'s team are ( X ) , ( Y ).'           (xN; "is" for a single team)

These parsers are reused downstream by the perturbation engine (M3).
"""

from __future__ import annotations

import re

_CTX_MARKER = "Temporal context:"
_ANS_MARKER = "### Answer:"

# One event of a TempReason L2/L3 context. The relation predicate varies by Wikidata
# property ("works for", "plays for", "is the head coach of", "holds the position of",
# …) and may be subject- or object-first, so the parser captures the whole 'head'
# (the full subject+relation+object text) and only structures the fixed date tail. Years can be
# 3-4 digits (historical entities, e.g. 988). Separating the answer entity out of the
# head is deferred to M3, which localises it via 'answer_orig' membership in the context.
_L2L3_EVENT = re.compile(
    r"^(?P<head>.+?) "
    r"from (?P<start_month>\w+), (?P<start_year>\d{3,4}) "
    r"to (?P<end_month>\w+), (?P<end_year>\d{3,4})$"
)
# Events are joined with ".. " (each event's own "." + the ". " separator); single
# periods inside org names ("Doncaster Rovers F.C.") never form this double-period.
_L2L3_SPLIT = re.compile(r"\.\.\s+")

# One event of a TimeQA context. The relation varies (team, spouse, school,
# education, position, …) and each interval endpoint may carry a month:
#   '[<Mon> ]<YYYY> - [<Mon> ]<YYYY> : <lhs> are/is ( X ) , ( Y )'
# '<lhs>' is usually '<Entity>'s <relation>' but is sometimes a bare subject
# ('Galatasaray S.K. (football) is ( Unknown )'), so the possessive split is best-effort.
# Values may themselves contain parentheses, so they are extracted with a balanced
# scanner ('_paren_groups'), not a flat regex.
_TIMEQA_EVENT = re.compile(
    r"^(?P<start>(?:\w+ )?\d{3,4})(?: - (?P<end>(?:\w+ )?\d{3,4}))? : "
    r"(?P<lhs>.+?) (?:are|is) (?P<values_str>.+)$"
)
_ENDPOINT = re.compile(r"^(?:(?P<month>\w+) )?(?P<year>\d{3,4})$")
# Event boundary: a closing paren followed by a period + whitespace.
_TIMEQA_SPLIT = re.compile(r"(?<=\))\.\s+")


def _paren_groups(s: str) -> list[str]:
    """Return the top-level parenthesised contents of 's', honouring nesting."""
    groups: list[str] = []
    depth = 0
    start = None
    for i, ch in enumerate(s):
        if ch == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                raise ContextParseError(f"unbalanced parens: {s!r}")
            if depth == 0 and start is not None:
                groups.append(s[start:i].strip())
                start = None
    if depth != 0:
        raise ContextParseError(f"unbalanced parens: {s!r}")
    return groups

# Conflict-class applicability per split (doc 4.2, substrate-driven).
_APPLICABLE = {
    "tempreason_l2_test": ["C1", "C2"],
    "tempreason_l3_test": ["C2", "C3"],
    "timeqa_easy_test": ["C1", "C2"],
    "timeqa_hard_test": ["C1", "C2"],
}


class ContextParseError(ValueError):
    """Raised when a prompt/context does not match its expected template."""


def isolate_context(prompt: str) -> str:
    """Return the raw context substring between 'Temporal context' and '### Answer:'."""
    i = prompt.find(_CTX_MARKER)
    j = prompt.find(_ANS_MARKER)
    if i == -1 or j == -1 or j < i:
        raise ContextParseError("prompt missing 'Temporal context:'/'### Answer:' markers")
    return prompt[i + len(_CTX_MARKER) : j].strip()


def strip_context(prompt: str) -> str:
    """Return the closed-book prompt: preamble + Question + '### Answer:', context removed.

    Deletes only the 'Temporal context:' block (the one place the gold answer appears),
    keeping the verbatim preamble and the question. This is the 'tiser_no_context' prompt.
    """
    i = prompt.find(_CTX_MARKER)
    j = prompt.find(_ANS_MARKER)
    if i == -1 or j == -1 or j < i:
        raise ContextParseError("prompt missing 'Temporal context:'/'### Answer:' markers")
    head = prompt[:i].rstrip()
    tail = prompt[j:]
    return f"{head}\n    \n    {tail}"


def inject_empty_note(
    prompt_no_context: str,
    note: str = "Temporal context: (none provided — answer from your own knowledge.)",
) -> str:
    """Turn a 'tiser_no_context' prompt into the 'tiser_empty_note' variant.

    Inserts an explicit empty-context placeholder just before '### Answer:'.
    """
    head, sep, tail = prompt_no_context.rpartition(_ANS_MARKER)
    if not sep:
        raise ContextParseError("closed-book prompt missing '### Answer:' marker")
    return f"{head.rstrip()}\n    \n    {note}\n    \n    {sep}{tail}"


def parse_l2l3(ctx: str) -> list[dict]:
    """Parse a TempReason L2/L3 context into a list of dated relation events.

    Each event = '{head, start_month, start_year, end_month, end_year, raw}' where
    'head' is the full '<subject> <relation> <object>' text (predicate-agnostic).
    """
    events = []
    for piece in _L2L3_SPLIT.split(ctx):
        piece = piece.strip().rstrip(".").strip()  # drop the trailing sentence period(s)
        if not piece:
            continue
        m = _L2L3_EVENT.match(piece)
        if not m:
            raise ContextParseError(f"unparseable L2/L3 event: {piece!r}")
        d = m.groupdict()
        d["start_year"] = int(d["start_year"])
        d["end_year"] = int(d["end_year"])
        d["raw"] = piece
        events.append(d)
    if not events:
        raise ContextParseError(f"no L2/L3 events parsed from: {ctx!r}")
    return events


def parse_timeqa(ctx: str) -> list[dict]:
    """Parse a TimeQA context into a list of dated relation intervals.

    Each event = '{start_year, end_year, entity, relation, values[], raw}'; the gold
    answer for an interval is the space-join of that interval's 'values'.
    """
    events = []
    for piece in _TIMEQA_SPLIT.split(ctx):
        piece = piece.strip()
        if not piece:
            continue
        m = _TIMEQA_EVENT.match(piece)
        if not m:
            raise ContextParseError(f"unparseable TimeQA event: {piece!r}")
        start = _ENDPOINT.match(m.group("start"))
        # A bare time-point ("Feb 1998 : …") has no end; treat it as a zero-width interval.
        end = _ENDPOINT.match(m.group("end")) if m.group("end") else start
        if not start or not end:
            raise ContextParseError(f"unparseable TimeQA interval: {piece!r}")
        values = _paren_groups(m.group("values_str"))
        if not values:
            raise ContextParseError(f"no values in TimeQA event: {piece!r}")
        # Best-effort possessive split: "<entity>'s <relation>" or a bare subject.
        lhs = m.group("lhs").strip()
        entity, sep, relation = lhs.partition("'s ")
        events.append(
            {
                "start_month": start.group("month"),
                "start_year": int(start.group("year")),
                "end_month": end.group("month"),
                "end_year": int(end.group("year")),
                "entity": entity.strip() if sep else lhs,
                "relation": relation.strip() if sep else None,
                "values": values,
                "raw": piece,
            }
        )
    if not events:
        raise ContextParseError(f"no TimeQA events parsed from: {ctx!r}")
    return events


def parse_context(split: str, ctx: str) -> list[dict]:
    """Dispatch to the right structured parser for an in-scope split."""
    if split in ("tempreason_l2_test", "tempreason_l3_test"):
        return parse_l2l3(ctx)
    if split in ("timeqa_easy_test", "timeqa_hard_test"):
        return parse_timeqa(ctx)
    raise ContextParseError(f"no parser for split {split!r}")


# --- Serializers (inverse of the parsers above; used by the perturbation engine M3) ---
# Each serializer renders the exact released template so that an edited event list is
# re-emitted byte-faithfully. The contract is structural round-trip, asserted by callers:
#   parse_l2l3(serialize_l2l3(events)) == events   (and the TimeQA equivalent).


def serialize_l2l3(events: list[dict]) -> str:
    """Render TempReason L2/L3 events back into their context string.

    Events are joined by ".. " (each sentence's own "." + the ". " separator) and the
    whole string ends with a single "."; inverse of 'parse_l2l3'.
    """
    if not events:
        raise ContextParseError("cannot serialize empty L2/L3 event list")
    sentences = [
        f"{e['head']} from {e['start_month']}, {e['start_year']} "
        f"to {e['end_month']}, {e['end_year']}"
        for e in events
    ]
    return ".. ".join(sentences) + "."


def _endpoint_str(month: str | None, year: int) -> str:
    """Render a TimeQA interval endpoint: '<Mon> <YYYY>' or bare '<YYYY>'."""
    return f"{month} {year}" if month else f"{year}"


def _timeqa_event_str(e: dict) -> str:
    """Render one TimeQA interval; inverse of a single 'parse_timeqa' event."""
    start = _endpoint_str(e["start_month"], e["start_year"])
    end = _endpoint_str(e["end_month"], e["end_year"])
    lhs = f"{e['entity']}'s {e['relation']}" if e["relation"] else e["entity"]
    verb = "is" if len(e["values"]) == 1 else "are"
    values = " , ".join(f"( {v} )" for v in e["values"])
    return f"{start} - {end} : {lhs} {verb} {values}"


def serialize_timeqa(events: list[dict]) -> str:
    """Render TimeQA events back into their context string.

    Events are joined by ". " (closing paren of one event + the ". " separator); unlike
    L2/L3, the released TimeQA context carries no trailing period. Inverse of 'parse_timeqa'.
    The verb (are/is) is re-derived from value count since the parser discards it; zero-width
    point intervals (start == end) round-trip either way.
    """
    if not events:
        raise ContextParseError("cannot serialize empty TimeQA event list")
    return ". ".join(_timeqa_event_str(e) for e in events)


def serialize_context(split: str, events: list[dict]) -> str:
    """Dispatch to the right serializer for an in-scope split."""
    if split in ("tempreason_l2_test", "tempreason_l3_test"):
        return serialize_l2l3(events)
    if split in ("timeqa_easy_test", "timeqa_hard_test"):
        return serialize_timeqa(events)
    raise ContextParseError(f"no serializer for split {split!r}")


def _strip_raw(events: list[dict]) -> list[dict]:
    """Drop the provenance-only 'raw' field for structural comparison.

    'raw' is the verbatim source fragment (stale after any edit, and not byte-recoverable
    for zero-width TimeQA point intervals which may render as '<Mon> <YYYY>' rather than
    '<Mon> <YYYY> - <Mon> <YYYY>'); it is not part of the canonical structured event.
    """
    return [{k: v for k, v in e.items() if k != "raw"} for e in events]


def assert_round_trip(split: str, events: list[dict]) -> str:
    """Serialize 'events', re-parse, and assert structural equality. Returns the string.

    The safety net for byte-template fidelity: every edited context must survive this
    before it is emitted by M3. Compares structured fields only (the 'raw' provenance
    field is excluded, see '_strip_raw').
    """
    rendered = serialize_context(split, events)
    reparsed = parse_context(split, rendered)
    if _strip_raw(reparsed) != _strip_raw(events):
        raise ContextParseError(
            f"round-trip mismatch for split {split!r}:\n"
            f"  events:   {events!r}\n  reparsed: {reparsed!r}\n  rendered: {rendered!r}"
        )
    return rendered


def inject_context(prompt_no_context: str, ctx: str) -> str:
    """Insert a 'Temporal context: <ctx>' block before '### Answer:' in a closed-book prompt.

    Mirrors 'inject_empty_note' exactly but with a real (edited) context, so the verbatim
    4-tag preamble + question stay byte-identical to training. Used by M4 (tiser style).
    """
    head, sep, tail = prompt_no_context.rpartition(_ANS_MARKER)
    if not sep:
        raise ContextParseError("closed-book prompt missing '### Answer:' marker")
    return f"{head.rstrip()}\n    \n    {_CTX_MARKER} {ctx}\n    \n    {sep}{tail}"


def applicable_classes(split: str) -> list[str]:
    """Conflict classes applicable to a split's substrate (doc 4.2)."""
    return list(_APPLICABLE[split])
