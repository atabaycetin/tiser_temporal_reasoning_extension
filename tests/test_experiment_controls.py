from __future__ import annotations

import copy
import shutil

import pytest

from scripts.prepare_study_bundle import notebook
from src.experiment.artifacts import digest, jsonl, read, sha256, source_snapshot, write
from src.experiment.evaluation import EvaluationStore, apply_tennis_view
from src.experiment.statistics import MACRO_SPLITS, compare, forgetting_gate, holm, mcnemar, paired_rows, token_gate
from src.experiment.study import (archive_incomplete_training, artifact, canonical_test_rows,
                                  register, replay_rows, resolve_reference)
from src.train.exposure import Exposure, closest_token_steps, planned_exposure, schedule_batches


@pytest.mark.parametrize("interval,expected", [([-0.08, -0.03], "clear_forgetting"), ([-0.01, 0.01], "non_inferior"),
                                                 ([-0.03, 0], "inconclusive"), ([-0.03, -0.02], "inconclusive"), ([-0.02, 0], "inconclusive")])
def test_forgetting_branches(interval, expected):
    assert forgetting_gate(interval) == expected


@pytest.mark.parametrize("tokens,trigger", [(89, True), (90, False), (100, False), (110, False), (111, True)])
def test_token_threshold(tokens, trigger):
    assert token_gate(100, tokens)["sensitivity_required"] == trigger


def test_schedule_and_resumed_counter_equal_uninterrupted():
    meta = [{"input_tokens": 10 + i, "supervised_tokens": 5 + i} for i in range(7)]
    planned = planned_exposure(meta, 4, 2, 2)
    batches = list(schedule_batches(len(meta), 2, 8))
    counter = Exposure()
    for i, b in enumerate(batches[:4], 1):
        counter.observe([meta[j]["input_tokens"] for j in b], [meta[j]["supervised_tokens"] for j in b])
        if i % 2 == 0:
            counter.update(i // 2)
    counter = Exposure.restore(counter.to_dict(), 2)
    for i, b in enumerate(batches[4:], 5):
        counter.observe([meta[j]["input_tokens"] for j in b], [meta[j]["supervised_tokens"] for j in b])
        if i % 2 == 0:
            counter.update(i // 2)
    assert counter.to_dict() == planned
    assert planned["examples"] == 16  # repeated exposures, not unique rows
    with pytest.raises(ValueError, match="step mismatch"):
        Exposure.restore(planned, 3)


def test_token_plan_chooses_closest_completed_update():
    meta = [{"input_tokens": 30, "supervised_tokens": 10}] * 3
    assert closest_token_steps(meta, 175, 2, 2)["max_steps"] == 4
    assert closest_token_steps(meta, 185, 2, 2)["max_steps"] == 5
    assert closest_token_steps(meta, 1, 2, 2)["max_steps"] == 1


def test_ood_missing_and_duplicate_ids_get_stable_derivative_ids():
    rows = [{"question_id": q, "dataset_name": "tot_semantic_test", "answer": "E1", "prompt": str(i)}
            for i, q in enumerate(["", "0", "0", "unique"])]
    values, mapping = canonical_test_rows(rows)
    assert len(mapping) == 3 and len({r["question_id"] for r in values}) == 4
    assert canonical_test_rows(rows)[0] == values
    assert rows[0]["question_id"] == ""
    assert values[-1]["question_id"] == "unique"
    rows[0]["dataset_name"] = "tgqa_test"
    with pytest.raises(ValueError, match="primary benchmark"):
        canonical_test_rows(rows)


def prediction(i, *, dataset="tennis_temporal", em=1, gold="Yes"):
    return {"question_id": str(i), "dataset_name": dataset, "gold": gold, "em": em, "f1": float(em),
            "raw_generation": "<answer>Yes</answer>", "pred_answer": "Yes", "malformed": False,
            "category": "yes_no_before_after", "tags": []}


def spec(rows):
    return {"ordered_ids": [[r["dataset_name"], r["question_id"]] for r in rows], "ordered_gold": [r["gold"] for r in rows]}


def test_evaluation_resume_has_exact_rows_and_rejects_changes(tmp_path):
    rows = [prediction(i) for i in range(3)]
    store = EvaluationStore(tmp_path / "eval", spec(rows))
    store.add(rows[:2])
    with pytest.raises(ValueError, match="incomplete"):
        store.finish()
    store = EvaluationStore(tmp_path / "eval", spec(rows), resume=True)
    assert store.rows == rows[:2]
    store.add(rows[2:])
    assert store.finish() == rows
    assert read(tmp_path / "eval/completion.json")["status"] == "complete"
    changed = spec(rows)
    changed["ordered_gold"][0] = "No"
    with pytest.raises(ValueError, match="Frozen artifact differs"):
        EvaluationStore(tmp_path / "eval", changed, resume=True)
    with pytest.raises(FileExistsError):
        EvaluationStore(tmp_path / "eval", spec(rows))


def test_evaluation_rejects_wrong_order_and_corrupt_chunks(tmp_path):
    rows = [prediction(i) for i in range(2)]
    store = EvaluationStore(tmp_path / "eval", spec(rows))
    with pytest.raises(ValueError, match="ID/order/gold"):
        store.add(list(reversed(rows)))
    store.add(rows)
    p = next((tmp_path / "eval/prediction_chunks").glob("*.json"))
    data = read(p)
    data["rows"][0]["em"] = 0
    write(p, data)
    with pytest.raises(ValueError, match="chunk hash"):
        EvaluationStore(tmp_path / "eval", spec(rows), resume=True)


def test_audited_view_changes_gold_and_denominator_without_changing_predictions(tmp_path):
    original = [prediction(1), prediction(2), prediction(3)]
    p = tmp_path / "input.json"
    write(p, [{**r, "answer": r["gold"]} for r in original])
    entries = [{"dataset_name": r["dataset_name"], "question_id": r["question_id"], "original_gold": "Yes",
                "gold": "No" if i == 0 else "Yes", "eligible": i != 1} for i, r in enumerate(original)]
    view = {"input_sha256": sha256(p), "n_primary": 2, "rows": entries}
    view["sha256"] = digest(view)
    v = tmp_path / "view.json"
    write(v, view)
    result = apply_tennis_view(original, v, p)
    assert len(result) == 2 and result[0]["gold"] == "No" and result[0]["em"] == 0
    assert original[0]["gold"] == "Yes"


def test_paired_alignment_and_holm():
    a = [prediction(1), prediction(2)]
    with pytest.raises(ValueError, match="ID/order/gold"):
        paired_rows(a, list(reversed(a)))
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert mcnemar([1, 1, 0], [0, 0, 0])["p_exact_two_sided"] == pytest.approx(0.5)


def test_stratified_bootstrap_weights_splits_equally_and_excludes_ood():
    pytest.importorskip("numpy")
    a, b = [], []
    for index, name in enumerate(MACRO_SPLITS):
        for i in range(2 if index == 0 else 7):
            a.append(prediction(i, dataset=name, em=0))
            b.append(prediction(i, dataset=name, em=int(index == 0)))
    a.append(prediction(99, dataset="tot_semantic_test", em=1))
    b.append(prediction(99, dataset="tot_semantic_test", em=0))
    first, draws = compare(a, b, domain="tiser", replicates=100)
    second, repeated = compare(a, b, domain="tiser", replicates=100)
    assert first == second
    assert (draws == repeated).all()
    assert first["em"]["delta"] == pytest.approx(0.2)
    assert first["em"]["ci95"] == pytest.approx([0.2, 0.2])
    assert first["excluded_ood_splits"] == ["tot_semantic_test"]
    with pytest.raises(ValueError, match="Missing required"):
        compare(a[2:], b[2:], domain="tiser", replicates=10)


def training_row(i, name):
    return {"question_id": str(i), "dataset_name": name, "prompt": f"{name} unique prompt {i}", "answer": "Yes",
            "output": "<reasoning>Yes</reasoning><timeline>Event before</timeline><reflection>Consistent</reflection><answer>Yes</answer>"}


def test_replay_is_deterministic_and_filters_leakage_before_sampling():
    tennis = [training_row(i, "tennis_temporal") for i in range(600)]
    source = [training_row(i, "original_train") for i in range(230)]
    leaked = copy.deepcopy(source[0])
    original = copy.deepcopy(source)
    mixed, summary = replay_rows(tennis, source, [leaked], eligible=lambda r: int(r["question_id"]) >= 5)
    repeated, second = replay_rows(tennis, source, [leaked], eligible=lambda r: int(r["question_id"]) >= 5)
    assert mixed == repeated and summary == second and source == original
    assert len(mixed) == 800
    assert sum(r["replay_source"] == "tiser_original" for r in mixed) == 200
    assert not any(r["dataset_name"] == "original_train" and int(r["question_id"]) < 5 for r in mixed)
    with pytest.raises(ValueError, match="leakage"):
        replay_rows(tennis, source, [tennis[0]])


def test_incomplete_training_restart_is_archived_without_deletion(tmp_path):
    write(tmp_path / "training/C1R/training_spec.json", {"partial": True})
    write(tmp_path / "models/C1R/partial.json", {"partial": True})
    record = archive_incomplete_training(tmp_path, "C1R")
    archive = tmp_path / "failed_attempts/C1R/attempt-001"
    assert record and (archive / "training/training_spec.json").is_file()
    assert (archive / "model/partial.json").is_file()
    assert not (tmp_path / "training/C1R").exists()
    assert jsonl(tmp_path / "failed_attempts.jsonl")[0]["condition"] == "C1R"


def test_source_snapshot_tracks_experiment_dependencies():
    files = source_snapshot()["files"]
    assert "requirements-experiments.txt" in files
    assert "pyproject.toml" in files


def test_study_artifact_reference_survives_directory_move(tmp_path):
    study = tmp_path / "original/study"
    payload = study / "data/value.json"
    write(payload, {"value": 42})
    write(study / "registry.json", {"artifacts": {}})
    register(study, "value", payload)
    assert read(study / "registry.json")["artifacts"]["value"]["reference"]["scope"] == "study"
    moved = tmp_path / "copied/study"
    moved.parent.mkdir(parents=True)
    shutil.move(study, moved)
    assert artifact(moved, "value") == moved / "data/value.json"
    assert read(artifact(moved, "value")) == {"value": 42}


def test_scoped_reference_rejects_escape(tmp_path):
    with pytest.raises(ValueError, match="escapes"):
        resolve_reference(tmp_path, {"scope": "study", "path": "../outside"})


def test_colab_notebook_covers_complete_conditional_workflow():
    cells = notebook()["cells"]
    source = "\n".join("".join(cell["source"]) for cell in cells)
    for required in (
        "fetch_retention_data.py",
        "experiment('init')",
        "experiment('prepare-data')",
        "training_smoke",
        "experiment('gate')",
        "train_if_needed('C1R')",
        "train_if_needed('R25')",
        "train_if_needed('R25-T')",
        "results/tennis_semantic_audit_v2",
        "experiment('freeze-final'",
        "experiment('statistics')",
    ):
        assert required in source
    assert "/content/drive/Othercomputers/My Mac/Desktop/Folders/Documents n Stuff/Polito/DNLP/Project/tiser_temporal_reasoning_extension" in source
    assert "results/forgetting_replay/study_v2" in source
    for removed in ("WORKSPACE_ZIP", "tiser_study_workspace.zip", "zipfile", "extractall"):
        assert removed not in source
