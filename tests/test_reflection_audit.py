import pytest

from scripts.conflict.audit_reflections_openai import (
    PASS_PROMPTS,
    make_job,
    validate_judgment,
    write_or_validate_run_spec,
)


def test_request_hash_changes_with_model() -> None:
    first = make_job(
        "a" * 64,
        "judge_a",
        "gpt-5.5-2026-04-23",
        PASS_PROMPTS["judge_a"],
        "AUDIT_ID: x\nREFLECTION_START\ntext\nREFLECTION_END",
    )
    second = make_job(
        "a" * 64,
        "judge_a",
        "different-model",
        PASS_PROMPTS["judge_a"],
        "AUDIT_ID: x\nREFLECTION_START\ntext\nREFLECTION_END",
    )
    assert first["request_sha256"] != second["request_sha256"]


def test_positive_judgment_requires_exact_evidence() -> None:
    valid = {
        "label": "explicit_conflict",
        "mention_kind": "memory_context_mismatch",
        "evidence_quote": "contradicts what I remember",
        "rationale": "The reflection explicitly identifies a mismatch.",
    }
    validate_judgment(valid, "This contradicts what I remember from before.")

    invalid = dict(valid, evidence_quote="a paraphrase not in the source")
    with pytest.raises(ValueError, match="exact reflection substring"):
        validate_judgment(invalid, "This contradicts what I remember from before.")


def test_resume_refuses_a_changed_run_spec(tmp_path) -> None:
    path = tmp_path / "run_spec.json"
    write_or_validate_run_spec(path, {"model": "fixed"}, resume=False)
    write_or_validate_run_spec(path, {"model": "fixed"}, resume=True)
    with pytest.raises(RuntimeError, match="Cannot resume"):
        write_or_validate_run_spec(path, {"model": "changed"}, resume=True)

