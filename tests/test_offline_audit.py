from __future__ import annotations

import copy
from pathlib import Path

import pytest

from src.audit import offline as audit
from src.experiment.artifacts import digest, freeze, read, sha256, write


def setup_audit(tmp_path, kind="semantic", count=2):
    items, mapping = {}, {}
    for i in range(count):
        payload = {"context": f"Event {i} finished before the delay.", "question": "Was it before?", "gold": "Yes"}
        if kind == "reflection":
            payload = {"reflection": f"Claim {i} contradicts what I remember."}
        h = digest({"kind": kind, "payload": payload})
        aid = f"{kind}-{h[:24]}"
        items[aid] = {"audit_id": aid, "kind": kind, "payload": payload, "source_sha256": h}
        if kind == "reflection":
            mapping[aid] = [{"cell": "base__tiser", "row": {
                "reflection_text": payload["reflection"], "conflict_type": "object",
                "faithful_em": 1, "reflection_mentions_conflict": True,
            }}]
        else:
            mapping[aid] = [{"question_id": f"q{i}", "split": "dev", "category": "temporal"}]
    manifest = {"version": audit.VERSION, "kind": kind, "source_files": {}, "item_counts": {kind: count},
                "items_sha256": digest(items), "mapping_sha256": digest(mapping),
                "malformed_sha256": digest([]), "requested_model": audit.DEFAULT_REQUESTED_MODEL}
    for name, value in (("manifest", manifest), ("items", items), ("mapping", mapping), ("malformed", [])):
        write(tmp_path / f"{name}.json", value)
    write(tmp_path / "task_protocol.json", audit.task_protocol(kind=kind))
    for judge in ("judge_a", "judge_b"):
        audit.export_batches(tmp_path, kind, judge, list(items.values()))
    audit.write_judge_prompt(tmp_path / "task_bundles/JUDGE_PROMPT.txt")
    return items


def response(tmp_path, judge="judge_a", kind="semantic", label=None):
    batch = read(next((tmp_path / "packs" / kind / judge).glob("*.json")))
    judgments = []
    for item in batch["items"]:
        positive = kind == "reflection"
        field = "reflection" if positive else "context"
        judgments.append({"audit_id": item["audit_id"], "source_sha256": item["source_sha256"],
                          "label": label or ("explicit_conflict" if positive else "supported"),
                          "corrected_answer": "No" if label == "wrong_gold" else None,
                          "mention_kind": "memory_context_mismatch" if positive else "none",
                          "evidence": [{"field": field, "quote": item["payload"][field]}],
                          "rationale": f"The stated event order supports the decision for {item['audit_id']}."})
    return {"batch_id": batch["batch_id"], "batch_sha256": batch["batch_sha256"], "pass": judge,
            "judged_at": "2026-09-08T10:00:00+00:00",
            "observed_model_label": audit.DEFAULT_REQUESTED_MODEL,
            "reasoning_effort": "high", "judgments": judgments}


def import_data(tmp_path, data, name="response.json"):
    path = tmp_path / name
    write(path, data)
    return audit.import_response(tmp_path, path)


def test_prepared_real_coverage_and_blinding():
    items, mapping, _, malformed = audit.collect()
    assert sum(len(mapping[i]) for i in items if i.startswith("semantic-")) == 1122
    assert sum(i["kind"] == "trace" for i in items.values()) == 650
    assert sum(i["kind"] == "reflection" for i in items.values()) == 2295
    assert len(malformed) == 4
    for item in items.values():
        batch = audit.make_batch(item["kind"], "judge_a", [item])
        assert "mapping" not in batch
        assert not {"question_id", "split", "cell", "faithful_em", "category"} & set(item["payload"])


def test_positive_evidence_is_exact(tmp_path):
    items = setup_audit(tmp_path, "reflection")
    data = response(tmp_path, kind="reflection")
    data["judgments"][0]["evidence"][0]["quote"] = "not in the reflection"
    result = import_data(tmp_path, data)
    assert result["accepted"] == 0 and len(result["errors"]) == 1
    assert audit.accepted(tmp_path) == {}
    assert len(list((tmp_path / "raw_responses").glob("*"))) == 1


@pytest.mark.parametrize("mutation", ["duplicate", "unknown", "hash", "missing_timestamp"])
def test_invalid_batch_response_is_rejected(tmp_path, mutation):
    setup_audit(tmp_path)
    data = response(tmp_path)
    if mutation == "duplicate":
        data["judgments"][1] = data["judgments"][0]
    elif mutation == "unknown":
        data["judgments"][0]["audit_id"] = "foreign"
    elif mutation == "hash":
        data["batch_sha256"] = "changed"
    else:
        del data["judged_at"]
    result = import_data(tmp_path, data)
    assert result["errors"] and not result["accepted"]


def test_response_schema_and_reasoning_effort_are_strict(tmp_path):
    setup_audit(tmp_path)
    extra = response(tmp_path)
    extra["unexpected"] = True
    assert not import_data(tmp_path, extra)["accepted"]
    wrong_effort = response(tmp_path)
    wrong_effort["reasoning_effort"] = "medium"
    assert not import_data(tmp_path, wrong_effort, "effort.json")["accepted"]
    wrong_model = response(tmp_path)
    wrong_model["observed_model_label"] = "unknown"
    assert not import_data(tmp_path, wrong_model, "model.json")["accepted"]


def test_missing_items_remain_pending_and_reexport(tmp_path):
    setup_audit(tmp_path)
    data = response(tmp_path)
    data["judgments"].pop()
    assert import_data(tmp_path, data)["accepted"] == 0
    assert audit.summarize(tmp_path)["status"] == "pending"
    paths = audit.adjudicate(tmp_path)
    assert sum(len(read(p)["items"]) for p in paths) == 4


def test_first_valid_response_wins_and_journal_detects_tampering(tmp_path):
    setup_audit(tmp_path)
    data = response(tmp_path)
    assert import_data(tmp_path, data)["accepted"] == 2
    assert import_data(tmp_path, data)["accepted"] == 0
    newer = copy.deepcopy(data)
    newer["judgments"][0]["label"] = "underdetermined"
    assert import_data(tmp_path, newer, "retry.json")["accepted"] == 0
    assert all(j["label"] == "supported" for j in audit.accepted(tmp_path).values())
    raw = tmp_path / "raw_responses" / f"{sha256(tmp_path / 'response.json')}.json"
    raw.write_text("corrupted")
    with pytest.raises(ValueError, match="hash mismatch"):
        audit.accepted(tmp_path)


def test_agreed_corrections_still_require_adjudication(tmp_path):
    setup_audit(tmp_path)
    for judge in ("judge_a", "judge_b"):
        assert not import_data(tmp_path, response(tmp_path, judge, label="wrong_gold"), judge + ".json")["errors"]
    assert audit.summarize(tmp_path)["status"] == "pending"
    paths = audit.adjudicate(tmp_path)
    assert all(read(p)["pass"] == "adjudicator" for p in paths)
    result = import_data(tmp_path, response(tmp_path, "adjudicator", label="wrong_gold"), "adjudicated.json")
    assert not result["errors"]
    assert audit.summarize(tmp_path)["status"] == "complete"


def test_quarantined_output_cannot_be_imported(tmp_path):
    setup_audit(tmp_path)
    p = tmp_path / "response.json"
    write(p, response(tmp_path))
    write(tmp_path / "quarantine.json", {"rejected_responses": {sha256(p): "regex violation"}})
    result = audit.import_response(tmp_path, p)
    assert not result["accepted"]
    assert "quarantined" in result["errors"][0]["error"]


def test_frozen_item_tampering_is_rejected(tmp_path):
    setup_audit(tmp_path)
    values = read(tmp_path / "items.json")
    next(iter(values.values()))["payload"]["gold"] = "changed"
    write(tmp_path / "items.json", values)
    with pytest.raises(ValueError, match="inputs changed"):
        audit.summarize(tmp_path)


def test_progress_is_resumable_and_judge_prompt_is_frozen(tmp_path):
    setup_audit(tmp_path)
    assert import_data(tmp_path, response(tmp_path))["accepted"] == 2
    progress = audit.update_progress(tmp_path)
    assert progress["primary_completed"] == 2
    assert progress["primary_judgments"] == 4
    prompt = tmp_path / "task_bundles/JUDGE_PROMPT.txt"
    prompt.write_text("changed")
    with pytest.raises(ValueError, match="prompt"):
        audit.load_state(tmp_path)


def test_views_require_semantic_audit_to_be_complete(tmp_path):
    setup_audit(tmp_path)
    with pytest.raises(ValueError, match="semantic audit must be complete"):
        audit.freeze_views(tmp_path, tmp_path)


def test_reflection_summary_does_not_wait_for_other_audit_kinds(tmp_path):
    setup_audit(tmp_path, kind="reflection")
    for judge in ("judge_a", "judge_b"):
        assert not import_data(tmp_path, response(tmp_path, judge, kind="reflection"), judge + ".json")["errors"]
    summary = audit.summarize(tmp_path)
    assert summary["status"] == "complete"
    assert summary["completed"] == {"reflection": 2}
    assert summary["reflection_cells"]["base__tiser"]["all_rows"] == 2


def test_reflection_mention_kind_must_match_label(tmp_path):
    setup_audit(tmp_path, kind="reflection")
    positive = response(tmp_path, kind="reflection")
    positive["judgments"][0]["mention_kind"] = "none"
    assert not import_data(tmp_path, positive, "positive-none.json")["accepted"]

    negative = response(tmp_path, kind="reflection")
    for judgment in negative["judgments"]:
        judgment["label"] = "no_explicit_conflict"
        judgment["mention_kind"] = "other"
        judgment["evidence"] = []
    assert not import_data(tmp_path, negative, "negative-other.json")["accepted"]


def test_disagreement_denominator_includes_adjudicated_unscorable_rows():
    rows = [
        {"final_label": "explicit_conflict", "conflict_type": "object", "faithful_em": 0,
         "judge_a_label": "explicit_conflict", "judge_b_label": "explicit_conflict",
         "reflection_mentions_conflict": True},
        {"final_label": "unscorable", "conflict_type": "object", "faithful_em": 0,
         "judge_a_label": "explicit_conflict", "judge_b_label": "unscorable",
         "reflection_mentions_conflict": False},
    ]
    result = audit.reflection.summarize_rows(rows)["two_pass_disagreement"]
    assert result["count"] == 1 and result["n"] == 2


def test_prepare_requires_one_kind(tmp_path):
    with pytest.raises(ValueError, match="exactly one kind"):
        audit.prepare(tmp_path)


def test_complete_pass_bundle_preserves_internal_batches(tmp_path):
    items = setup_audit(tmp_path, kind="reflection", count=51)
    paths = sorted((tmp_path / "packs/reflection/judge_a").glob("*.json"))
    bundle_path = audit.export_task_bundle(
        tmp_path, "reflection", "judge_a", paths, name="reflection-judge_a-primary"
    )
    bundle = read(bundle_path)
    assert bundle["batch_count"] == 2
    assert bundle["item_count"] == len(items) == 51
    assert bundle["batch_ids"] == [batch["batch_id"] for batch in bundle["batches"]]
    assert bundle["bundle_sha256"] == audit.digest({k: v for k, v in bundle.items() if k != "bundle_sha256"})


def test_directory_import_accepts_one_complete_pass(tmp_path):
    setup_audit(tmp_path, count=2)
    response_dir = tmp_path / "judge_a_responses"
    response_dir.mkdir()
    write(response_dir / "batch.json", response(tmp_path, judge="judge_a"))
    result = audit.import_responses(tmp_path, response_dir, task_id="judge-a-task")
    assert result["files"] == 1
    assert result["accepted"] == 2
    assert result["errors"] == []


def test_directory_import_rejects_mixed_judge_passes(tmp_path):
    setup_audit(tmp_path, count=2)
    response_dir = tmp_path / "mixed_responses"
    response_dir.mkdir()
    write(response_dir / "a.json", response(tmp_path, judge="judge_a"))
    write(response_dir / "b.json", response(tmp_path, judge="judge_b"))
    result = audit.import_responses(tmp_path, response_dir, task_id="mixed-task")
    assert result["accepted"] == 0
    assert "exactly one judge pass" in result["errors"][0]["error"]
    assert audit.accepted(tmp_path) == {}
