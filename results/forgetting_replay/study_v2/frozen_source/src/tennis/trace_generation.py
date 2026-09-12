"""Prompting and validation helpers for tennis TISER trace generation."""

from __future__ import annotations

import re
from typing import Any


REQUIRED_SECTIONS = ("reasoning", "timeline", "reflection", "answer")
MIN_TISER_OUTPUT_CHARS = 80


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_answer(value: str) -> str:
    """Normalize answers for exact-match filtering."""
    return _clean_text(value).casefold()


def build_trace_generation_prompt(
    context: str, question: str, answer: str, category: str
) -> str:
    """Build an offline prompt for external generation of a TISER trace."""
    return "\n".join(
        [
            "Generate a TISER training trace for the tennis temporal QA example below.",
            "Use only the provided context. Do not use outside tennis knowledge.",
            "The final answer must be exactly the provided gold answer.",
            "Do not add markdown fences, bullets outside the XML-like sections, or commentary.",
            "Output only these four sections, in this order:",
            "<reasoning>...</reasoning>",
            "<timeline>...</timeline>",
            "<reflection>...</reflection>",
            "<answer>...</answer>",
            "",
            "Requirements:",
            "- Keep the reasoning concise.",
            "- Make the timeline explicit and ordered.",
            "- In the reflection, briefly verify that the final answer follows from the context.",
            "- The text inside <answer> must exactly equal the gold answer.",
            "",
            f"Category: {category.strip()}",
            "",
            "Context:",
            context.strip(),
            "",
            "Question:",
            question.strip(),
            "",
            "Gold answer:",
            answer.strip(),
        ]
    )


def _extract_tag_content(output: str, tag: str) -> list[str]:
    pattern = rf"<{tag}>\s*(.*?)\s*</{tag}>"
    return [match.strip() for match in re.findall(pattern, output, flags=re.DOTALL)]


def extract_answer_from_output(output: str) -> str:
    """Extract the first <answer>...</answer> value from a generated trace."""
    if not isinstance(output, str):
        return ""
    answers = _extract_tag_content(output, "answer")
    if not answers:
        return ""
    return _clean_text(answers[0])


def validate_tiser_output(output: str, gold_answer: str) -> dict[str, Any]:
    """Validate generated TISER output against the required tags and gold answer."""
    output_is_string = isinstance(output, str)
    text = output if output_is_string else ""
    stripped = text.strip()
    section_contents = {
        section: _extract_tag_content(text, section) for section in REQUIRED_SECTIONS
    }
    extracted_answer = extract_answer_from_output(text)

    result: dict[str, Any] = {
        "is_valid": False,
        "errors": [],
        "output_not_empty": bool(stripped),
        "output_not_too_short": len(stripped) >= MIN_TISER_OUTPUT_CHARS,
        "extracted_answer": extracted_answer,
        "normalized_answer": normalize_answer(extracted_answer),
        "normalized_gold_answer": normalize_answer(gold_answer),
        "answer_matches_gold": False,
    }

    for section in REQUIRED_SECTIONS:
        contents = section_contents[section]
        has_section = bool(contents and any(content.strip() for content in contents))
        result[f"has_{section}"] = has_section
        result[f"{section}_count"] = len(contents)

    if not output_is_string:
        result["errors"].append("output is not a string")
    if not result["output_not_empty"]:
        result["errors"].append("output is empty")
    if not result["output_not_too_short"]:
        result["errors"].append(
            f"output is too short; minimum is {MIN_TISER_OUTPUT_CHARS} characters"
        )

    for section in REQUIRED_SECTIONS:
        if not result[f"has_{section}"]:
            result["errors"].append(f"missing or empty <{section}> section")

    if not extracted_answer:
        result["errors"].append("answer could not be extracted")
    else:
        result["answer_matches_gold"] = (
            result["normalized_answer"] == result["normalized_gold_answer"]
        )
        if not result["answer_matches_gold"]:
            result["errors"].append("answer mismatch")

    result["malformed_tags"] = any(
        not result[f"has_{section}"] for section in REQUIRED_SECTIONS
    )
    result["is_valid"] = not result["errors"]
    return result
