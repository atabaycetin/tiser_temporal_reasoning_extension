from __future__ import annotations

from pathlib import Path

from src.tennis.eval import render_markdown_report


def test_markdown_report_uses_path_relative_to_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "results" / "condition"
    predictions = output_dir / "predictions.jsonl"
    report = output_dir / "metrics_report.md"
    metrics = {
        "overall": {
            "n": 1,
            "em": 1.0,
            "f1": 1.0,
            "malformed_count": 0,
            "malformed_rate": 0.0,
        },
        "per_category": {},
        "answer_type_confusion": {},
        "category_answer_type_confusion": {},
        "malformed_examples": [],
    }

    markdown = render_markdown_report(metrics, predictions, report)

    assert "- Predictions: `predictions.jsonl`" in markdown
    assert str(tmp_path) not in markdown
