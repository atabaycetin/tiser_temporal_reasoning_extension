"""Plan and optionally run tennis domain-adaptation evaluations."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = Path("results/tennis_domain_adaptation")
SCRIPT_PATH = RESULTS_ROOT / "comparisons/run_tennis_experiments.sh"


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    condition: str
    eval_set: str
    test_file: Path
    output_dir: Path
    adapter_dir: Path | None
    no_adapter: bool
    prompt_style: str = "tiser"
    blocked_note: str | None = None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    experiments = build_experiments(args)
    commands = [build_command(exp, args) for exp in experiments]
    missing = collect_missing_prerequisites(args, experiments)

    script_path = resolve_repo_path(SCRIPT_PATH)
    write_shell_script(script_path, experiments, commands, force=args.force)

    print_plan(experiments, commands, missing, script_path)

    if args.execute:
        if missing:
            print("\n[tennis-plan] Refusing to execute while prerequisites are missing.")
            return 2
        return execute_plan(experiments, commands, force=args.force)

    print("\n[tennis-plan] Dry run only. Pass --execute to run the commands.")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a reproducible command plan for tennis domain-adaptation evaluations."
    )
    parser.add_argument("--tennis-test", default="data/tennis/tennis_test.json")
    parser.add_argument(
        "--tiser-sample", default="data/tennis/original_tiser_eval_sample.json"
    )
    parser.add_argument(
        "--original-tiser-adapter", default="model/tiser_qwen7b_full/adapter"
    )
    parser.add_argument(
        "--tennis-adapter", default="model/tiser_tennis_only_qwen7b/adapter"
    )
    parser.add_argument(
        "--mixed-adapter", default="model/tiser_tennis_mixed_replay_qwen7b/adapter"
    )
    parser.add_argument("--config", default="config/config_tennis.yaml")
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Sample limit for smoke evaluations. Defaults to 100.",
    )
    parser.add_argument(
        "--include-blocked-adapter-experiments",
        action="store_true",
        help=(
            "Also print original TISER, tennis-only, and mixed-replay adapter "
            "commands. These require artifacts that are not present by default."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run the planned evaluations. Without this flag, only print/write commands.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing completed evaluation outputs.",
    )
    return parser.parse_args(argv)


def build_experiments(args: argparse.Namespace) -> list[Experiment]:
    tennis_test = Path(args.tennis_test)
    tiser_sample = Path(args.tiser_sample)
    original_adapter = Path(args.original_tiser_adapter)
    tennis_adapter = Path(args.tennis_adapter)
    mixed_adapter = Path(args.mixed_adapter)

    tennis_scored = RESULTS_ROOT / "scored"
    tiser_scored = RESULTS_ROOT / "scored_original_tiser_sample"

    experiments = [
        Experiment(
            experiment_id="E0-standard",
            condition="base_qwen_standard",
            eval_set="tennis_test",
            test_file=tennis_test,
            output_dir=tennis_scored / "base_qwen_standard_smoke_100",
            adapter_dir=None,
            no_adapter=True,
            prompt_style="standard",
        ),
        Experiment(
            experiment_id="E0-tiser",
            condition="base_qwen_tiser",
            eval_set="tennis_test",
            test_file=tennis_test,
            output_dir=tennis_scored / "base_qwen_tiser_smoke_100",
            adapter_dir=None,
            no_adapter=True,
            prompt_style="tiser",
        ),
    ]

    if not args.include_blocked_adapter_experiments:
        return experiments

    experiments.extend(
        [
            Experiment(
                experiment_id="E1",
                condition="original_tiser",
                eval_set="tennis_test",
                test_file=tennis_test,
                output_dir=tennis_scored / "original_tiser",
                adapter_dir=original_adapter,
                no_adapter=False,
                blocked_note="requires model/tiser_qwen7b_full/adapter",
            ),
            Experiment(
                experiment_id="E2",
                condition="tennis_only",
                eval_set="tennis_test",
                test_file=tennis_test,
                output_dir=tennis_scored / "tennis_only",
                adapter_dir=tennis_adapter,
                no_adapter=False,
                blocked_note="requires validated tennis traced data and a trained adapter",
            ),
            Experiment(
                experiment_id="E3",
                condition="mixed_replay",
                eval_set="tennis_test",
                test_file=tennis_test,
                output_dir=tennis_scored / "mixed_replay",
                adapter_dir=mixed_adapter,
                no_adapter=False,
                blocked_note="requires original TISER data plus a trained mixed-replay adapter",
            ),
            Experiment(
                experiment_id="E1-forgetting",
                condition="original_tiser",
                eval_set="original_tiser_sample",
                test_file=tiser_sample,
                output_dir=tiser_scored / "original_tiser",
                adapter_dir=original_adapter,
                no_adapter=False,
                blocked_note="requires original TISER eval sample and adapter",
            ),
            Experiment(
                experiment_id="E2-forgetting",
                condition="tennis_only",
                eval_set="original_tiser_sample",
                test_file=tiser_sample,
                output_dir=tiser_scored / "tennis_only",
                adapter_dir=tennis_adapter,
                no_adapter=False,
                blocked_note="requires original TISER eval sample and tennis-only adapter",
            ),
            Experiment(
                experiment_id="E3-forgetting",
                condition="mixed_replay",
                eval_set="original_tiser_sample",
                test_file=tiser_sample,
                output_dir=tiser_scored / "mixed_replay",
                adapter_dir=mixed_adapter,
                no_adapter=False,
                blocked_note="requires original TISER eval sample and mixed-replay adapter",
            ),
        ]
    )
    return experiments


def collect_missing_prerequisites(
    args: argparse.Namespace, experiments: list[Experiment]
) -> list[str]:
    missing: list[str] = []
    required_files = {"config": Path(args.config)}
    for exp in experiments:
        required_files[f"{exp.eval_set} for {exp.experiment_id}"] = exp.test_file
    if any(exp.condition == "tennis_only" for exp in experiments):
        required_files["tennis traced train data"] = Path(
            "data/tennis/tennis_train_traced_full.json"
        )
    if any(exp.condition == "mixed_replay" for exp in experiments):
        required_files["original TISER train data"] = Path("data/TISER_train.json")
        required_files["mixed replay train data"] = Path(
            "data/tennis/tennis_mixed_replay_train.json"
        )

    for label, path in sorted(required_files.items()):
        if not resolve_repo_path(path).exists():
            missing.append(f"{label}: {path.as_posix()}")

    seen_adapters: set[Path] = set()
    for exp in experiments:
        if exp.adapter_dir is None or exp.adapter_dir in seen_adapters:
            continue
        seen_adapters.add(exp.adapter_dir)
        if not resolve_repo_path(exp.adapter_dir).is_dir():
            missing.append(f"adapter for {exp.condition}: {exp.adapter_dir.as_posix()}")
    return missing


def build_command(exp: Experiment, args: argparse.Namespace) -> list[str]:
    command = [
        "python",
        "scripts/tennis/evaluate_tennis.py",
        "--config",
        Path(args.config).as_posix(),
        "--test-file",
        exp.test_file.as_posix(),
        "--condition",
        exp.condition,
        "--prompt-style",
        exp.prompt_style,
        "--output-dir",
        exp.output_dir.as_posix(),
    ]
    if exp.no_adapter:
        command.append("--no-adapter")
    elif exp.adapter_dir is not None:
        command.extend(["--adapter-dir", exp.adapter_dir.as_posix()])
    if args.limit is not None:
        command.extend(["--limit", str(args.limit)])
    return command


def write_shell_script(
    script_path: Path,
    experiments: list[Experiment],
    commands: list[list[str]],
    *,
    force: bool,
) -> None:
    script_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated by scripts/tennis/run_experiment_plan.py",
        "# Set FORCE=1 or regenerate with --force to overwrite existing metrics.json files.",
        f"FORCE=${{FORCE:-{1 if force else 0}}}",
        "",
    ]
    for exp, command in zip(experiments, commands):
        metrics_path = (exp.output_dir / "metrics.json").as_posix()
        lines.extend(
            [
                f'echo "[tennis-plan] {exp.experiment_id} {exp.condition} on {exp.eval_set}"',
                f'if [ -f "{metrics_path}" ] && [ "$FORCE" != "1" ]; then',
                f'  echo "[tennis-plan] SKIP existing {metrics_path} (set FORCE=1 to overwrite)"',
                "else",
                indent_shell_command(command),
                "fi",
                "",
            ]
        )
    script_path.write_text("\n".join(lines), encoding="utf-8")


def indent_shell_command(command: list[str]) -> str:
    rendered = render_shell_command(command)
    return "  " + rendered.replace(" \\\n  ", " \\\n    ")


def render_shell_command(command: list[str]) -> str:
    return " \\\n  ".join(shell_quote(part) for part in command)


def shell_quote(value: str) -> str:
    if value and all(ch.isalnum() or ch in "-_./:=+" for ch in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def print_plan(
    experiments: list[Experiment],
    commands: list[list[str]],
    missing: list[str],
    script_path: Path,
) -> None:
    print("# Tennis Experiment Plan")
    print(f"\nRunnable shell script: {relative_path(script_path)}")
    print("\n## Commands")
    for exp, command in zip(experiments, commands):
        print(f"\n### {exp.experiment_id}: {exp.condition} on {exp.eval_set}")
        print(render_shell_command(command))

    print("\n## Expected result folders")
    for exp in experiments:
        print(f"- {exp.output_dir.as_posix()}")

    blocked = [exp for exp in experiments if exp.blocked_note]
    if blocked:
        print("\n## Blocked experiment notes")
        for exp in blocked:
            print(f"- {exp.experiment_id}: {exp.blocked_note}")

    print("\n## Missing prerequisites")
    if missing:
        for item in missing:
            print(f"- MISSING {item}")
    else:
        print("- none")


def execute_plan(
    experiments: list[Experiment], commands: list[list[str]], *, force: bool
) -> int:
    for exp, command in zip(experiments, commands):
        metrics_path = resolve_repo_path(exp.output_dir / "metrics.json")
        if metrics_path.exists() and not force:
            print(
                f"[tennis-plan] SKIP {exp.condition} on {exp.eval_set}: "
                f"{relative_path(metrics_path)} exists"
            )
            continue
        print(f"[tennis-plan] RUN {exp.experiment_id}: {exp.condition} on {exp.eval_set}")
        completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0


def resolve_repo_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return REPO_ROOT / value


def relative_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
