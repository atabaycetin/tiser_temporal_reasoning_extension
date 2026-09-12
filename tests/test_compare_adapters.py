from __future__ import annotations

import csv
import json
from pathlib import Path

from conftest import load_repo_module


CANONICAL_MIXED_ADAPTER = "model/tiser_tennis_mixed_replay_qwen7b/adapter"


def load_compare_module():
    return load_repo_module("scripts/tennis/compare_adapters.py", "test_compare_module")


def write_metrics(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def fake_metrics(
    condition: str,
    *,
    adapter_dir: str | None = None,
    prompt_style: str = "tiser",
    no_adapter: bool = False,
    em: float = 0.5,
    f1: float = 0.75,
) -> dict:
    return {
        "condition": condition,
        "prompt_style": prompt_style,
        "model_name": "fake-model",
        "no_adapter": no_adapter,
        "adapter_dir": adapter_dir,
        "overall": {
            "n": 2,
            "em": em,
            "f1": f1,
            "malformed_count": 1,
            "malformed_rate": 0.5,
        },
        "per_category": {
            "yes_no_before_after": {
                "n": 2,
                "em": 0.5,
                "f1": 0.75,
                "malformed_count": 1,
                "malformed_rate": 0.5,
            }
        },
    }


def test_missing_metrics_are_loaded_as_missing(tmp_path: Path) -> None:
    compare = load_compare_module()

    loaded = compare.load_condition_metrics([tmp_path / "scored" / "tennis_only"])

    assert loaded["tennis_only"]["status"] == "MISSING"
    assert loaded["tennis_only"]["overall"] == {}


def test_compare_main_marks_expected_plan_missing_runs_without_crashing(tmp_path: Path) -> None:
    compare = load_compare_module()
    results_dir = tmp_path / "results"
    output_dir = tmp_path / "comparison_out"
    write_metrics(
        results_dir / "scored" / "base_qwen_standard" / "metrics.json",
        fake_metrics("base_qwen_standard"),
    )

    compare.main(
        [
            "--results-dir",
            str(results_dir),
            "--output-dir",
            str(output_dir),
            "--expected-conditions",
        ]
    )

    comparison = json.loads((output_dir / "adapter_comparison.json").read_text())
    statuses = {row["condition"]: row["status"] for row in comparison["conditions"]}
    assert statuses["base_qwen_standard"] == "AVAILABLE"
    assert statuses["original_tiser"] == "MISSING"
    assert "MISSING" in (output_dir / "adapter_comparison.md").read_text()


def test_dynamic_discovered_metrics_are_included_without_missing_rows(tmp_path: Path) -> None:
    compare = load_compare_module()
    scored_dir = tmp_path / "results" / "scored"
    write_metrics(
        scored_dir / "base_qwen_standard_smoke_100" / "metrics.json",
        fake_metrics("base_qwen_standard_smoke_100", prompt_style="standard", no_adapter=True),
    )
    write_metrics(
        scored_dir / "tennis_only_trace50_smoke_100" / "metrics.json",
        fake_metrics("tennis_only_trace50_smoke_100", adapter_dir="model/adapter"),
    )
    (scored_dir / "empty_condition").mkdir(parents=True)

    condition_dirs = compare.discover_condition_dirs(scored_dir)
    loaded = compare.load_condition_metrics(condition_dirs)
    comparison = compare.build_comparison(loaded, baseline="original_tiser")
    statuses = {row["condition"]: row["status"] for row in comparison["conditions"]}

    assert list(statuses) == [
        "base_qwen_standard_smoke_100",
        "tennis_only_trace50_smoke_100",
    ]
    assert set(statuses.values()) == {"AVAILABLE"}


def test_available_metrics_are_loaded_correctly(tmp_path: Path) -> None:
    compare = load_compare_module()
    condition_dir = tmp_path / "scored" / "base_qwen_tiser"
    write_metrics(condition_dir / "metrics.json", fake_metrics("base_qwen_tiser"))

    loaded = compare.load_condition_metrics([condition_dir])
    comparison = compare.build_comparison(loaded, baseline="original_tiser")
    row = comparison["conditions"][0]

    assert row["condition"] == "base_qwen_tiser"
    assert row["status"] == "AVAILABLE"
    assert row["model_name"] == "fake-model"
    assert row["prompt_style"] == "tiser"
    assert row["no_adapter"] is False
    assert row["n"] == 2
    assert row["em"] == 0.5
    assert row["f1"] == 0.75


def test_canonical_mixed_replay_adapter_path_is_preserved(tmp_path: Path) -> None:
    compare = load_compare_module()
    condition_dir = tmp_path / "scored" / "mixed_replay"
    write_metrics(
        condition_dir / "metrics.json",
        fake_metrics("mixed_replay", adapter_dir=CANONICAL_MIXED_ADAPTER),
    )

    loaded = compare.load_condition_metrics([condition_dir])
    comparison = compare.build_comparison(loaded, baseline="original_tiser")

    assert comparison["conditions"][0]["condition"] == "mixed_replay"
    assert comparison["conditions"][0]["adapter_dir"] == CANONICAL_MIXED_ADAPTER


def test_markdown_uses_portable_recorded_adapter_path() -> None:
    compare = load_compare_module()
    absolute_paths = [
        (
            "/content/drive/example/tiser_temporal_reasoning_extension/"
            "model/example/adapter"
        ),
        (
            "C:\\Users\\example\\tiser_temporal_reasoning_extension\\"
            "tiser_temporal_reasoning_extension\\model\\example\\adapter"
        ),
    ]

    for absolute in absolute_paths:
        comparison = compare.build_comparison(
            {"example": fake_metrics("example", adapter_dir=absolute)},
            baseline="missing",
        )
        markdown = compare.render_markdown(comparison)

        assert "`model/example/adapter`" in markdown
        assert "/content/drive/" not in markdown
        assert "C:/Users/" not in markdown
        assert comparison["conditions"][0]["adapter_dir"] == absolute


def test_known_smoke_runs_are_summarized_and_outputs_are_written(tmp_path: Path) -> None:
    compare = load_compare_module()
    results_dir = tmp_path / "results"
    output_dir = tmp_path / "comparisons"
    smoke_runs = [
        ("base_qwen_standard_smoke_100", "standard", True, None, 0.21, 0.31),
        ("base_qwen_tiser_smoke_100", "tiser", True, None, 0.22, 0.32),
        ("tennis_only_trace50_smoke_100", "tiser", False, "model/adapter", 0.33, 0.44),
    ]
    for condition, prompt_style, no_adapter, adapter_dir, em, f1 in smoke_runs:
        write_metrics(
            results_dir / "scored" / condition / "metrics.json",
            fake_metrics(
                condition,
                prompt_style=prompt_style,
                no_adapter=no_adapter,
                adapter_dir=adapter_dir,
                em=em,
                f1=f1,
            ),
        )

    compare.main(["--results-dir", str(results_dir), "--output-dir", str(output_dir)])

    comparison = json.loads((output_dir / "adapter_comparison.json").read_text())
    rows = {row["condition"]: row for row in comparison["conditions"]}
    assert set(rows) == {condition for condition, *_rest in smoke_runs}
    assert rows["base_qwen_standard_smoke_100"]["prompt_style"] == "standard"
    assert rows["base_qwen_tiser_smoke_100"]["no_adapter"] is True
    assert rows["tennis_only_trace50_smoke_100"]["adapter_dir"] == "model/adapter"
    assert all(row["status"] == "AVAILABLE" for row in rows.values())

    markdown = (output_dir / "adapter_comparison.md").read_text(encoding="utf-8")
    assert "base_qwen_standard_smoke_100" in markdown
    assert "base_qwen_tiser_smoke_100" in markdown
    assert "tennis_only_trace50_smoke_100" in markdown

    csv_rows = list(
        csv.DictReader((output_dir / "adapter_comparison.csv").open(encoding="utf-8"))
    )
    assert {row["condition"] for row in csv_rows} == set(rows)
    assert (output_dir / "per_category_comparison.csv").exists()
