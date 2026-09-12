"""Prompt builders for tennis temporal QA."""

from __future__ import annotations


LEGACY_TISER_FORMAT_INSTRUCTION = "Return the final answer in the required format."

TISER_FORMAT_INSTRUCTION = "\n".join(
    [
        "Return only the final answer inside XML answer tags.",
        "For yes/no questions:",
        "<answer>Yes</answer>",
        "or",
        "<answer>No</answer>",
        "",
        "For span questions:",
        "<answer>the exact answer span</answer>",
        "",
        'Do not output the words "FINAL_ANSWER".',
        "Do not write anything after </answer>.",
    ]
)


def _build_tennis_prompt(context: str, question: str, format_instruction: str) -> str:
    return "\n".join(
        [
            "You are given a temporal context from the tennis domain and a question.",
            "Reason only over the events explicitly stated in the context.",
            "Use the temporal order, durations, overlaps, or tournament sequence when needed.",
            "",
            "Temporal context:",
            context.strip(),
            "",
            "Question:",
            question.strip(),
            "",
            format_instruction,
        ]
    )


def build_tennis_prompt(context: str, question: str) -> str:
    """Build the current strict-XML TISER-style tennis prompt."""
    return _build_tennis_prompt(context, question, TISER_FORMAT_INSTRUCTION)


def build_reported_tennis_prompt(context: str, question: str) -> str:
    """Build the legacy prompt stored in the data used for the reported training runs."""
    return _build_tennis_prompt(context, question, LEGACY_TISER_FORMAT_INSTRUCTION)


def ensure_tiser_format_instruction(prompt: str) -> str:
    """Upgrade legacy tennis prompts to the explicit answer format contract."""
    if TISER_FORMAT_INSTRUCTION in prompt:
        return prompt
    if LEGACY_TISER_FORMAT_INSTRUCTION in prompt:
        return prompt.replace(LEGACY_TISER_FORMAT_INSTRUCTION, TISER_FORMAT_INSTRUCTION)
    return "\n".join([prompt.rstrip(), "", TISER_FORMAT_INSTRUCTION])


def build_standard_prompt(context: str, question: str) -> str:
    """Build a direct-answer prompt for later prompt-format comparisons."""
    return "\n".join(
        [
            "You are given a temporal context from the tennis domain and a question.",
            "Reason only over the events explicitly stated in the context.",
            "",
            "Temporal context:",
            context.strip(),
            "",
            "Question:",
            question.strip(),
            "",
            "Return only the concise final answer.",
        ]
    )
