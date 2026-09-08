from __future__ import annotations

from pathlib import Path

from conftest import load_repo_module


def load_plan_module():
    return load_repo_module(
        "scripts/tennis/run_experiment_plan.py", "test_run_experiment_plan_module"
    )


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    return path


def test_default_plan_only_has_base_qwen_smoke_runs(tmp_path: Path, monkeypatch) -> None:
    plan = load_plan_module()
    monkeypatch.setattr(plan, "REPO_ROOT", tmp_path)
    config = touch(tmp_path / "config" / "config_tennis.yaml")
    tennis_test = touch(tmp_path / "data" / "tennis" / "tennis_test.json")
    args = plan.parse_args(
        ["--config", str(config), "--tennis-test", str(tennis_test)]
    )

    experiments = plan.build_experiments(args)

    assert [exp.condition for exp in experiments] == [
        "base_qwen_standard",
        "base_qwen_tiser",
    ]
    assert [exp.prompt_style for exp in experiments] == ["standard", "tiser"]
    assert all(exp.no_adapter for exp in experiments)
    assert all(exp.adapter_dir is None for exp in experiments)


def test_base_qwen_smoke_commands_do_not_require_adapters(tmp_path: Path, monkeypatch) -> None:
    plan = load_plan_module()
    monkeypatch.setattr(plan, "REPO_ROOT", tmp_path)
    config = touch(tmp_path / "config" / "config_tennis.yaml")
    tennis_test = touch(tmp_path / "data" / "tennis" / "tennis_test.json")
    args = plan.parse_args(
        ["--config", str(config), "--tennis-test", str(tennis_test)]
    )

    commands = [plan.build_command(exp, args) for exp in plan.build_experiments(args)]

    assert all("--no-adapter" in command for command in commands)
    assert all("--adapter-dir" not in command for command in commands)


def test_blocked_adapter_plan_reports_missing_prerequisites(
    tmp_path: Path, monkeypatch
) -> None:
    plan = load_plan_module()
    monkeypatch.setattr(plan, "REPO_ROOT", tmp_path)
    config = touch(tmp_path / "config" / "config_tennis.yaml")
    tennis_test = touch(tmp_path / "data" / "tennis" / "tennis_test.json")
    tiser_sample = touch(tmp_path / "data" / "tennis" / "original_tiser_eval_sample.json")
    args = plan.parse_args(
        [
            "--config",
            str(config),
            "--tennis-test",
            str(tennis_test),
            "--tiser-sample",
            str(tiser_sample),
            "--include-blocked-adapter-experiments",
        ]
    )

    missing = plan.collect_missing_prerequisites(args, plan.build_experiments(args))
    rendered = "\n".join(missing)

    assert "adapter for original_tiser: model/tiser_qwen7b_full/adapter" in rendered
    assert "tennis traced train data: data/tennis/tennis_train_traced_full.json" in rendered
    assert "original TISER train data: data/TISER_train.json" in rendered
    assert (
        "mixed replay train data: data/tennis/tennis_mixed_replay_train.json"
        in rendered
    )


def test_canonical_mixed_adapter_path_is_default() -> None:
    plan = load_plan_module()

    args = plan.parse_args([])

    assert args.mixed_adapter == "model/tiser_tennis_mixed_replay_qwen7b/adapter"
