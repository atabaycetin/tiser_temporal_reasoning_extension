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
        mapping[aid] = [{"question_id": f"q{i}", "split": "dev", "category": "temporal"}]
    manifest = {"version": audit.VERSION, "source_files": {}, "item_counts": {kind: count},
                "items_sha256": digest(items), "mapping_sha256": digest(mapping), "malformed_sha256": digest([])}
    for name, value in (("manifest", manifest), ("items", items), ("mapping", mapping), ("malformed", [])):
        write(tmp_path / f"{name}.json", value)
    write(tmp_path / "task_protocol.json", audit.task_protocol())
    for judge in ("judge_a", "judge_b"):
        audit.export_batches(tmp_path, kind, judge, list(items.values()))
        audit.write_guide(tmp_path / "packs" / kind / judge / "INSTRUCTIONS.md")
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
            "judged_at": "2026-09-08T10:00:00+00:00", "observed_model_label": "test-fixture",
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


def test_progress_is_resumable_and_guide_is_frozen(tmp_path):
    setup_audit(tmp_path)
    assert import_data(tmp_path, response(tmp_path))["accepted"] == 2
    progress = audit.update_progress(tmp_path)
    assert progress["primary_completed"] == 2
    assert progress["primary_judgments"] == 4
    guide = tmp_path / "packs/semantic/judge_a/INSTRUCTIONS.md"
    guide.write_text("changed")
    with pytest.raises(ValueError, match="guide"):
        audit.load_state(tmp_path)


def test_views_require_every_audit_kind_to_be_complete(tmp_path):
    setup_audit(tmp_path)
    with pytest.raises(ValueError, match="All semantic, trace, and reflection"):
        audit.freeze_views(tmp_path, tmp_path)
