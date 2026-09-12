"""Package the current reviewed workspace and generate a resumable Colab notebook."""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.experiment.artifacts import ROOT, source_snapshot, write
from src.experiment.study import C0, C1


def notebook():
    cells = []
    def md(text):
        cells.append({"cell_type": "markdown", "id": f"cell-{len(cells):02d}", "metadata": {}, "source": text.splitlines(True)})
    def code(text):
        cells.append({"cell_type": "code", "id": f"cell-{len(cells):02d}", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(True)})
    md("""# TISER conditional retention and replay study

This notebook invokes the repository CLIs. It runs C0/C1 retention first, trains
C1R and R25 only after clear forgetting, and runs token sensitivity only above
the predeclared 10% threshold. It contains no ablation or commit-management step.

Prepare `tiser_study_workspace.zip` with `scripts/prepare_study_bundle.py`, place it
in Drive, and select a single-GPU runtime. The workspace bundle contains the
current source and historical adapters; it does not require a new Git commit.
All runtime artifacts/checkpoints are persisted to Drive. Complete the Codex
file audits locally and refresh the bundle with frozen views before final cells.
The original 113 inputs are never used by smoke tests or model selection.
""")
    code("""from pathlib import Path
import os, sys, subprocess, json, zipfile
from google.colab import drive
drive.mount('/content/drive')
WORKSPACE_ZIP = Path('/content/drive/MyDrive/tiser_study_workspace.zip')
PROJECT_ROOT = Path('/content/tiser_temporal_reasoning_extension')
STUDY_DIR = Path('/content/drive/MyDrive/tiser_conditional_study_v1')
if not (PROJECT_ROOT / 'scripts/experiment.py').exists():
    if not WORKSPACE_ZIP.is_file():
        raise FileNotFoundError('Place the prepared workspace bundle at WORKSPACE_ZIP or set an existing PROJECT_ROOT.')
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(WORKSPACE_ZIP) as archive:
        if any(not (PROJECT_ROOT / name).resolve().is_relative_to(PROJECT_ROOT.resolve()) for name in archive.namelist()):
            raise ValueError('Unsafe archive path')
        archive.extractall(PROJECT_ROOT)
elif WORKSPACE_ZIP.is_file():
    with zipfile.ZipFile(WORKSPACE_ZIP) as archive:
        bundled_snapshot = archive.read('workspace_snapshot.json')
    extracted_snapshot = PROJECT_ROOT / 'workspace_snapshot.json'
    if not extracted_snapshot.is_file() or extracted_snapshot.read_bytes() != bundled_snapshot:
        raise RuntimeError(
            'The Drive bundle changed after this runtime extracted it. Start a fresh runtime '
            'or delete PROJECT_ROOT, then rerun this cell; STUDY_DIR on Drive is preserved.'
        )
os.chdir(PROJECT_ROOT)
""")
    md("## Install and verify the runtime\nUse the runtime's CUDA-matched PyTorch. Exact resolved package versions are recorded and checked on resume.")
    code("""subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '-r', 'requirements-experiments.txt'], check=True)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], check=True)
import torch
assert torch.cuda.is_available() and torch.cuda.device_count() == 1, 'Use one CUDA GPU.'
print(torch.cuda.get_device_name(0))
subprocess.run([sys.executable, '-m', 'pytest', '-q'], check=True)
""")
    md("## Prepare the frozen study and original-TISER populations")
    code("""def run(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=PROJECT_ROOT, check=True)

def experiment(command, *args):
    run('scripts/experiment.py', command, '--study-dir', STUDY_DIR, *args)

run('scripts/tennis/fetch_retention_data.py')
experiment('init')
experiment('prepare-data')
print(json.loads((STUDY_DIR / 'data/split_summary.json').read_text()))
""")
    md("""## Training-data smoke evaluation
The smoke input is five historical training rows. It cannot consume the 113 holdout.
It checks the 7B adapter/loading/generation path before the retention gate.
""")
    code("""from src.experiment.artifacts import freeze
from src.experiment.study import model_revision, save_config, C0
from src.utils.config import load_config
smoke_input = STUDY_DIR / 'smoke/training_inputs.json'
rows = json.loads((PROJECT_ROOT / 'data/tennis/tennis_train_traced_full.json').read_text())[:5]
freeze(smoke_input, rows)
cfg = load_config('config/config_tennis_7b_reported_best.yaml')
cfg.paths.test_file = str(smoke_input)
cfg.model.revision = model_revision(STUDY_DIR)
cfg.model.tokenizer_revision = cfg.model.revision
cfg.eval.batch_size = 4
smoke_cfg = save_config(STUDY_DIR / 'smoke/config.yaml', cfg)
run('scripts/tennis/evaluate_tennis.py', '--config', smoke_cfg, '--condition', 'training_smoke',
    '--adapter-dir', PROJECT_ROOT / C0, '--output-dir', STUDY_DIR / 'smoke/evaluation', '--resume')
""")
    md("## Measure forgetting before training replay")
    code("""for condition in ['C0', 'C1']:
    experiment('evaluate', '--condition', condition, '--domain', 'tiser', '--stage', 'selection', '--resume')
experiment('gate')
gate = json.loads((STUDY_DIR / 'forgetting_gate.json').read_text())
print(gate)
""")
    md("""## Conditional current control and replay
Checkpoints include optimizer, scheduler, RNG state and token counters. Completed
conditions are reused. An interruption resumes the latest complete checkpoint.
With no complete checkpoint, retain the failed directory and restart from C0
using the CLI's explicit restart-incomplete option.
""")
    code("""def train_if_needed(condition):
    registry = json.loads((STUDY_DIR / 'registry.json').read_text())
    if condition in registry['conditions']:
        print('Already complete:', condition)
        return
    checkpoints = sorted((STUDY_DIR / 'training' / condition / 'trainer').glob('checkpoint-*'),
                         key=lambda p: int(p.name.split('-')[-1]))
    required = ['optimizer.pt', 'scheduler.pt', 'rng_state.pth', 'trainer_state.json',
                'token_exposure.json', 'training_spec.json']
    checkpoints = [p for p in checkpoints if all((p / f).is_file() for f in required)
                   and any((p / f).is_file() for f in ['adapter_model.safetensors', 'adapter_model.bin'])]
    if checkpoints:
        flags = ['--resume-from-checkpoint', checkpoints[-1]]
    elif (STUDY_DIR / 'training' / condition).exists() or (STUDY_DIR / 'models' / condition).exists():
        flags = ['--restart-incomplete']
    else:
        flags = []
    experiment('train', '--condition', condition, *flags)

if gate['decision'] == 'clear_forgetting':
    experiment('replay-data')
    train_if_needed('C1R')
    train_if_needed('R25')
    experiment('token-gate')
    tokens = json.loads((STUDY_DIR / 'token_gate.json').read_text())
    print(tokens)
    if tokens['sensitivity_required']:
        train_if_needed('R25-T')
else:
    print('Replay stopped under the frozen rule:', gate['decision'])
""")
    md("""## Complete and freeze the Codex file audits
Import the individually judged A/B responses locally, prepare and import
adjudications, and run `scripts/audit.py summarize` followed by `freeze-views`.
Sync the completed `results/project_audit_v1` folder into this workspace. No
predictions are shown to the auditors. This cell deliberately stops while any
audit is pending; it never substitutes a partial audit for completion.
""")
    code("""AUDIT_DIR = PROJECT_ROOT / 'results/project_audit_v1'
run('scripts/audit.py', 'summarize', '--output-dir', AUDIT_DIR)
audit = json.loads((AUDIT_DIR / 'summary.json').read_text())
assert audit['status'] == 'complete', 'Complete all primary judgments and adjudications before final evaluation.'
run('scripts/audit.py', 'freeze-views', '--output-dir', AUDIT_DIR)
""")
    md("## Selection diagnostics and final campaign freeze\nAll triggered conditions remain in the campaign even when their selection scores disappoint.")
    code("""registry = json.loads((STUDY_DIR / 'registry.json').read_text())
conditions = list(registry['conditions'])
if not (STUDY_DIR / 'final_campaign.json').exists():
    for condition in conditions:
        for domain in ['tennis', 'tiser']:
            experiment('evaluate', '--condition', condition, '--domain', domain, '--stage', 'selection',
                       '--audit-dir', AUDIT_DIR, '--resume')
    experiment('freeze-final', '--audit-dir', AUDIT_DIR)
print(json.loads((STUDY_DIR / 'final_campaign.json').read_text()))
""")
    md("## One-time final evaluation\nResume only missing chunks of this frozen campaign. Final results cannot reopen training or selection.")
    code("""campaign = json.loads((STUDY_DIR / 'final_campaign.json').read_text())
for condition in campaign['conditions']:
    for domain in ['tennis', 'tiser']:
        experiment('evaluate', '--condition', condition, '--domain', domain, '--stage', 'final',
                   '--audit-dir', AUDIT_DIR, '--resume')
if not (STUDY_DIR / 'final_statistics/statistics.json').exists():
    experiment('statistics')
experiment('status')
""")
    md("""## Reporting
Use audited primary tennis scores with their actual eligible denominator and
show original-label scores separately. Original-TISER retention is the unweighted
five-split macro; ToT-semantic is secondary OOD evidence. Preserve bootstrap
replicates and Holm-adjusted per-split McNemar tables. A single training seed
does not measure training variability. Model-judge agreement does not establish
human-calibrated accuracy. The holdout prior-use statement remains qualified.
""")
    return {"cells": cells, "metadata": {"colab": {"name": "colab_conditional_retention.ipynb"},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"}}, "nbformat": 4, "nbformat_minor": 5}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--notebook-only", action="store_true")
    p.add_argument("--output", default="output/tiser_study_workspace.zip")
    args = p.parse_args(argv)
    value = notebook()
    for cell in value["cells"]:
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), "notebook-cell", "exec")
    write(ROOT / "notebooks/colab_conditional_retention.ipynb", value)
    if args.notebook_only:
        return
    roots = [ROOT / name for name in (
        "src", "scripts", "config", "tests", "docs", "data/tennis",
        "results/project_audit_v1", C0, C1,
    )]
    paths = {p for root in roots for p in root.rglob("*") if p.is_file()
             and "__pycache__" not in p.parts and "quarantine" not in p.parts
             and not any(part.startswith(".") for part in p.relative_to(ROOT).parts)}
    paths.update(ROOT / name for name in (
        "requirements.txt", "requirements-experiments.txt", "pyproject.toml", "LICENSE",
        "README.md", "report/DNLP_Temporal_Reasoning.tex",
        "notebooks/colab_conditional_retention.ipynb",
    ))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, path.relative_to(ROOT))
        archive.writestr("workspace_snapshot.json", json.dumps(source_snapshot(), indent=2))
    temporary.replace(output)
    print(f"Prepared {output.resolve()} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
