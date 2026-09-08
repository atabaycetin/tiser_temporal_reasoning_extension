from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tennis" / "audit_tennis_trace_coverage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_tennis_trace_coverage", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_tracked_trace_coverage_explains_600_cutoff() -> None:
    module = load_module()
    result = module.audit_coverage(
        read_json("data/tennis/tennis_train.json"),
        read_json("data/tennis/tennis_train_traced_50.json"),
        read_json("data/tennis/tennis_train_traced_full.json"),
        read_json(
            "results/tennis_domain_adaptation/trace_generation/"
            "batches_full/manifest.json"
        ),
    )

    assert result["status"] == "pass"
    assert result["counts"] == {
        "train": 785,
        "pilot": 50,
        "manifest_selected_after_pilot_exclusion": 735,
        "manifest_batches": 15,
        "consumed_complete_batches": 12,
        "reported_traced_full": 600,
        "ungenerated_tail": 135,
        "absent_from_reported_traced_full": 185,
    }
    assert all(result["checks"].values())
    assert result["boundaries"]["last_reported_traced_id"] == "tennis_000934"
    assert result["boundaries"]["first_ungenerated_tail_id"] == "tennis_000935"

