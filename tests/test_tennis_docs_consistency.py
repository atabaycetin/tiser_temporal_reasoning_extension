from __future__ import annotations

import re
from pathlib import Path

from conftest import REPO_ROOT


DOCS_DIR = REPO_ROOT / "docs" / "extensions" / "tennis_domain_adaptation"
STATUS_DOC = DOCS_DIR / "Current_Status_and_Next_Steps.md"
UNTRAINED_REPLAY_ADAPTERS = (
    "model/tiser_tennis_mixed_replay_qwen7b/adapter",
    "model/mixed_tennis_tiser_replay_qwen7b/adapter",
    "model/tiser_tennis_mixed_qwen7b/adapter",
)


def read_tennis_docs() -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8")
        for path in DOCS_DIR.rglob("*.md")
    }


def test_docs_do_not_claim_an_untrained_replay_adapter() -> None:
    combined = "\n".join(read_tennis_docs().values())

    for adapter_path in UNTRAINED_REPLAY_ADAPTERS:
        assert adapter_path not in combined


def test_docs_do_not_claim_original_tiser_results_without_any_result_artifact() -> None:
    adapter_exists = (REPO_ROOT / "model" / "tiser_qwen7b_full" / "adapter").is_dir()
    legacy_result_exists = (
        REPO_ROOT
        / "results"
        / "tennis_domain_adaptation"
        / "scored"
        / "original_tiser"
        / "metrics.json"
    ).exists()
    current_result_exists = (
        REPO_ROOT
        / "results"
        / "tennis_from_tiser_experiments"
        / "scored"
        / "original_tiser_qwen7b_test224"
        / "metrics.json"
    ).exists()
    if adapter_exists or legacy_result_exists or current_result_exists:
        return

    risky_line = re.compile(
        r"(original[_ ]tiser|tiser_qwen7b_full).*(we evaluated|results? show|"
        r"scores? (?:are|were|show)|transfers to tennis|improves|outperforms)",
        flags=re.IGNORECASE,
    )
    allowed_context = re.compile(
        r"(blocked|missing|cannot|requires|do not|not valid|not available|optional|"
        r"must not|after .*exists|if .*exists|claims)",
        flags=re.IGNORECASE,
    )
    offenders = []
    for path, text in read_tennis_docs().items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            if risky_line.search(line) and not allowed_context.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{line_number}: {line}")

    assert offenders == []


def test_status_doc_distinguishes_completed_results_and_limitations() -> None:
    text = STATUS_DOC.read_text(encoding="utf-8")

    assert "## Completed Tennis-Test Results" in text
    assert "### 0.5B Standalone Tennis Subexperiment" in text
    assert "### 7B Tennis-from-TISER Experiments" in text
    assert "## Remaining limitations" in text
    assert "## Reporting Rules" in text
    assert "## Completed conditional study" in text
    assert "base_qwen_standard_test224" in text
    assert "original_tiser_qwen7b_test224" in text
    assert "tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011" in text
    assert "replay was not run" in text
