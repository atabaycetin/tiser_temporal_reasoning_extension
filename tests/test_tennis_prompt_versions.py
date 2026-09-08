from __future__ import annotations

from src.tennis.build_dataset import convert_examples
from src.tennis.prompts import (
    LEGACY_TISER_FORMAT_INSTRUCTION,
    TISER_FORMAT_INSTRUCTION,
    build_reported_tennis_prompt,
)


def _example() -> dict:
    return {
        "question_id": "tennis_000001",
        "context": "Sinner held serve before Alcaraz changed rackets.",
        "question": "Did Sinner hold serve first?",
        "answer": "Yes",
        "category": "yes_no_before_after",
        "tags": ["yes_no_before_after"],
    }


def test_reported_prompt_version_preserves_historical_instruction() -> None:
    tiser, _, _ = convert_examples(
        [_example()],
        dataset_name="tennis_temporal",
        deterministic_output=True,
        tiser_prompt_builder=build_reported_tennis_prompt,
    )

    prompt = tiser[0]["prompt"]
    assert prompt.endswith(LEGACY_TISER_FORMAT_INSTRUCTION)
    assert TISER_FORMAT_INSTRUCTION not in prompt

