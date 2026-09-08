"""Conditional C0/C1 retention, C1R/R25 replay, and frozen final campaign."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

from src.experiment.artifacts import ROOT, append, digest, freeze, identity, jsonl, now, read, sha256, source_snapshot, tree_hash, validate_rows, write
from src.experiment.statistics import MACRO_SPLITS, analyze_spec, compare, token_gate
from src.train.exposure import closest_token_steps
from src.utils.config import load_config
from src.data.dataset import _load_records

C0 = "model/tiser_qwen7b_full/adapter"
C1 = "model/tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011/adapter"
EXPECTED_WEIGHTS = {"C0": "718cbd0a81a330073e64c59adcef88a1a92ec2922403cba641005fc23ca5d0fe",
                    "C1": "e1c28d374a61b5fa2c835e1c65a5c8537b3b286cd2d95b988341c05e1b0d6652"}
DEFAULT_STUDY = ROOT / "results/tennis_continual_adaptation/study_v2"
PINNED_DATA_REVISION = "7bdac51ea363a71b1805972b1d2c025f5cd173a4"


def path_reference(study, path):
    """Address artifacts portably when they live in the study or workspace."""
    study, path = Path(study).resolve(), Path(path).resolve()
    for scope, base in (("study", study), ("workspace", ROOT.resolve())):
        try:
            return {"scope": scope, "path": path.relative_to(base).as_posix()}
        except ValueError:
            pass
    return {"scope": "external", "path": str(path)}


def resolve_reference(study, reference):
    """Resolve new scoped references and legacy absolute/ROOT-relative strings."""
    if isinstance(reference, str):
        value = Path(reference)
        return value if value.is_absolute() else ROOT / value
    if not isinstance(reference, dict) or set(reference) != {"scope", "path"}:
        raise ValueError("Invalid artifact path reference")
    scope, value = reference["scope"], Path(reference["path"])
    if scope == "study":
        base = Path(study)
    elif scope == "workspace":
        base = ROOT
    elif scope == "external":
        if not value.is_absolute():
            raise ValueError("External artifact reference must be absolute")
        return value
    else:
        raise ValueError("Unknown artifact path scope")
    result = (base / value).resolve()
    try:
        result.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError("Artifact reference escapes its scope") from exc
    return result


def condition_adapter(study, condition):
    return resolve_reference(study, condition["adapter"])


def initialize(study):
    study = Path(study)
    if (study / "protocol.json").exists():
        verify(study)
        return read(study / "registry.json")
    conditions = {"C0": {"adapter": path_reference(study, ROOT / C0)},
                  "C1": {"adapter": path_reference(study, ROOT / C1)}}
    for name, value in conditions.items():
        adapter = condition_adapter(study, value)
        if sha256(adapter / "adapter_model.safetensors") != EXPECTED_WEIGHTS[name]:
            raise ValueError(f"Historical adapter hash mismatch: {name}")
        value["sha256"] = tree_hash(adapter)["sha256"]
    protocol = {"schema_version": 1, "seed": 42, "bootstrap_replicates": 10000,
                "forgetting_margin": 0.02, "tennis_non_inferiority_margin": 0.02,
                "token_mismatch_threshold": 0.10, "macro_splits": list(MACRO_SPLITS),
                "study_design": "conditional_minimum", "optimizer_steps": 74,
                "replay_count": 200, "tennis_count": 600, "training_seeds": [42],
                "final_comparisons": ["C1-C0/tiser", "C1-C0/tennis", "C1R-C0/tiser", "R25-C1R/tiser", "R25-C1R/tennis"],
                "sensitivity_comparisons": ["R25-T-C1R/tiser", "R25-T-C1R/tennis"],
                "gate": "upper95<-0.02 triggers C1R+R25; lower95>-0.02 stops; otherwise inconclusive and stops",
                "prior_113_use": {"team_record": "no known prior model-performance use",
                                   "repository_evidence": "No preserved repository evidence indicates prior model-performance use.",
                                   "independence_verified": False}}
    snapshot = source_snapshot()
    protocol["historical_data_sha256"] = {str(p.relative_to(ROOT)): sha256(p) for p in sorted((ROOT / "data/tennis").glob("*.json"))}
    freeze(study / "protocol.json", protocol)
    freeze(study / "source_snapshot.json", snapshot)
    for rel, expected in snapshot["files"].items():
        target = study / "frozen_source" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
        if sha256(target) != expected:
            raise ValueError("Failed source snapshot copy")
    registry = {"schema_version": 2, "created_at": now(), "protocol_sha256": digest(protocol),
                "source_sha256": snapshot["sha256"], "conditions": conditions, "artifacts": {},
                "status": "prepared; inference and training pending"}
    write(study / "registry.json", registry)
    return registry


def verify(study):
    study = Path(study)
    r = read(study / "registry.json")
    if digest(read(study / "protocol.json")) != r["protocol_sha256"]:
        raise ValueError("Preregistered protocol changed")
    if source_snapshot()["sha256"] != r["source_sha256"]:
        raise ValueError("Source/config changed since study freeze; create a new study version")
    for rel, expected in read(study / "protocol.json")["historical_data_sha256"].items():
        if sha256(ROOT / rel) != expected:
            raise ValueError(f"Historical tennis data changed: {rel}")
    for name, c in r["conditions"].items():
        if tree_hash(condition_adapter(study, c))["sha256"] != c["sha256"]:
            raise ValueError(f"Adapter changed: {name}")
    return r


def register(study, name, path):
    study = Path(study)
    r = read(study / "registry.json")
    value = {"reference": path_reference(study, path), "sha256": sha256(path)}
    if name in r["artifacts"] and r["artifacts"][name] != value:
        raise ValueError(f"Registered artifact changed: {name}")
    r["artifacts"][name] = value
    write(study / "registry.json", r)


def artifact(study, name):
    value = read(Path(study) / "registry.json")["artifacts"][name]
    path = resolve_reference(study, value.get("reference", value.get("path")))
    if sha256(path) != value["sha256"]:
        raise ValueError(f"Registered artifact hash mismatch: {name}")
    return path


def canonical_test_rows(rows):
    """The upstream OOD file reuses IDs; namespace those rows without editing it."""
    result, mapping = [], []
    counts = Counter((r.get("dataset_name"), r.get("question_id")) for r in rows)
    for index, row in enumerate(rows):
        value = dict(row)
        if not str(row.get("question_id") or "").strip() or counts[(row.get("dataset_name"), row.get("question_id"))] > 1:
            if row.get("dataset_name") != "tot_semantic_test":
                raise ValueError("Invalid/duplicate primary benchmark ID")
            value["question_id"] = f"tot_semantic_row_{index:06d}_{digest(row)[:16]}"
            mapping.append({"source_row": index, "source_question_id": row.get("question_id"),
                            "question_id": value["question_id"], "source_row_sha256": digest(row)})
        result.append(value)
    validate_rows(result)
    return result, mapping


def prepare_data(study, train_file, test_file, source_manifest):
    from scripts.tennis.build_tiser_eval_sample import sample_records, build_complement
    study = Path(study)
    verify(study)
    provenance = read(source_manifest)
    if provenance.get("revision") != PINNED_DATA_REVISION:
        raise ValueError("Original TISER source revision differs from the preregistered revision")
    train, raw_test = _load_records(str(train_file)), _load_records(str(test_file))
    test, id_mapping = canonical_test_rows(raw_test)
    validate_rows(train)
    validate_rows(test)
    for name, path in (("TISER_train.json", train_file), ("TISER_test.json", test_file)):
        if provenance["files"][name]["sha256"] != sha256(path):
            raise ValueError("Original data hash differs from source provenance")
    for row in [*train, *test]:
        if not all(isinstance(row.get(k), str) and row[k].strip() for k in ("question", "prompt")):
            raise ValueError("Incomplete original-TISER evaluator input")
    sampled, summary = sample_records(test, per_split=100, seed=42)
    complement = build_complement(test, sampled)
    for population in (sampled, complement):
        if not set(MACRO_SPLITS) <= {r["dataset_name"] for r in population}:
            raise ValueError("A required macro split is empty after partitioning")
    for key, rows in (("retention_selection", sampled), ("retention_final", complement)):
        path = study / "data" / f"{key}.json"
        freeze(path, rows)
        register(study, key, path)
    canonical_path = study / "data" / "original_test_canonical.json"
    freeze(canonical_path, test)
    register(study, "original_test_canonical", canonical_path)
    freeze(study / "data" / "ood_id_mapping.json", id_mapping)
    summary["ood_ids_namespaced"] = len(id_mapping)
    p = study / "data" / "source.json"
    freeze(p, {**provenance, "local_train": path_reference(study, train_file),
               "local_test": path_reference(study, test_file)})
    register(study, "original_data_source", p)
    freeze(study / "data" / "split_summary.json", summary)
    return summary


def leakage_key(row):
    return " ".join(row["prompt"].casefold().split())


def replay_rows(tennis, original_train, evaluation, *, seed=42, count=200, eligible=None):
    """Sample only validated, length-eligible original training rows."""
    import random
    from scripts.tennis.train_tennis import PLACEHOLDER_MARKERS
    from src.tennis.trace_generation import extract_answer_from_output, normalize_answer
    validate_rows(tennis)
    validate_rows(original_train)
    if len(tennis) != 600:
        raise ValueError("R25 requires exactly 600 historical tennis rows")
    forbidden_ids = {identity(r) for r in evaluation}
    forbidden_text = {leakage_key(r) for r in evaluation}
    if any(identity(r) in forbidden_ids or leakage_key(r) in forbidden_text for r in tennis):
        raise ValueError("Tennis training/evaluation leakage")
    tennis_text = {leakage_key(r) for r in tennis}
    seen, pool, rejected = set(), [], []
    shuffled = list(original_train)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    for row in shuffled:
        reason = None
        prompt = row.get("prompt", "")
        output = row.get("output", "")
        key = leakage_key(row)
        if identity(row) in forbidden_ids or key in forbidden_text or key in tennis_text:
            reason = "evaluation_or_tennis_overlap"
        elif key in seen:
            reason = "duplicate_prompt"
        elif not output or any(marker in output.casefold() for marker in PLACEHOLDER_MARKERS):
            reason = "missing_or_placeholder_trace"
        elif any(f"<{tag}>" not in output or f"</{tag}>" not in output for tag in ("reasoning", "timeline", "reflection", "answer")):
            reason = "trace_structure"
        elif normalize_answer(extract_answer_from_output(output)) != normalize_answer(row["answer"]):
            reason = "trace_gold_mismatch"
        elif eligible and not eligible(row):
            reason = "sequence_length"
        if reason:
            rejected.append({"id": list(identity(row)), "reason": reason})
        else:
            seen.add(key)
            pool.append({**row, "replay_source": "tiser_original"})
            if len(pool) == count:
                break
    if len(pool) != count:
        raise ValueError("Not enough valid, disjoint original-TISER replay rows")
    mixed = [{**r, "replay_source": "tennis"} for r in tennis] + pool
    rng.shuffle(mixed)
    return mixed, {"seed": seed, "tennis_records": len(tennis), "tiser_replay_records": len(pool),
                   "rejected_candidates": rejected, "ordered_ids": [list(identity(r)) for r in mixed],
                   "ordered_ids_sha256": digest([identity(r) for r in mixed])}


def run_command(command):
    subprocess.run([sys.executable, *command], cwd=ROOT, check=True)


def save_config(path, cfg):
    import yaml
    serialized = json.loads(json.dumps(cfg))
    path = Path(path)
    text = yaml.safe_dump(serialized, sort_keys=False)
    if path.exists() and path.read_text() != text:
        raise ValueError(f"Resolved config changed: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def model_revision(study):
    path = Path(study) / "model_revision.json"
    if path.exists():
        return read(path)["revision"]
    from huggingface_hub import model_info
    revision = model_info("Qwen/Qwen2.5-7B-Instruct").sha
    freeze(path, {"model": "Qwen/Qwen2.5-7B-Instruct", "revision": revision})
    register(study, "model_revision", path)
    return revision


def eval_condition(study, condition, domain, stage, *, audit_dir, resume=False):
    study = Path(study)
    registry = verify(study)
    if condition not in registry["conditions"]:
        raise ValueError(f"Unknown/untrained condition: {condition}")
    if (study / "final_campaign.json").exists() and stage == "selection":
        raise ValueError("Selection is closed after the final campaign is frozen")
    if stage == "final":
        campaign = read(artifact(study, "final_campaign"))
        if condition not in campaign["conditions"]:
            raise ValueError("Condition was not preregistered for the final campaign")
        for entry in campaign["artifact_hashes"]:
            if sha256(resolve_reference(study, entry["reference"])) != entry["sha256"]:
                raise ValueError("Final campaign artifact changed")
        if sha256(ROOT / "data/tennis/tennis_dev.json") != campaign["tennis_input_sha256"]:
            raise ValueError("Final tennis inputs changed")
    output = study / "evaluations" / stage / domain / condition
    adapter = condition_adapter(study, registry["conditions"][condition])
    config = load_config(str(ROOT / ("config/config_retention_7b.yaml" if domain == "tiser" else "config/config_tennis_7b_reported_best.yaml")))
    config.model.revision = model_revision(study)
    config.model.tokenizer_revision = config.model.revision
    config.eval.batch_size = 4
    config.eval.max_samples_per_split = None
    config.eval.do_sample = False
    config.eval.require_complete_splits = domain == "tiser"
    config.run_name = condition
    if domain == "tiser":
        data = artifact(study, "retention_selection" if stage == "selection" else "retention_final")
        config.paths.test_file = str(data)
        config.paths.output_dir = str(output.parent)
        path = save_config(study / "configs" / f"{stage}_{domain}_{condition}.yaml", config)
        command = ["scripts/evaluate.py", "--config", str(path), "--adapter-dir", str(adapter)]
    else:
        split = "test" if stage == "selection" else "dev"
        view = Path(audit_dir) / "views" / f"tennis_{split}.json"
        if not view.is_file():
            raise ValueError("Freeze the audited tennis view before evaluation")
        config.paths.test_file = str(ROOT / f"data/tennis/tennis_{split}.json")
        path = save_config(study / "configs" / f"{stage}_{domain}_{condition}.yaml", config)
        command = ["scripts/tennis/evaluate_tennis.py", "--config", str(path), "--adapter-dir", str(adapter),
                   "--condition", condition, "--output-dir", str(output), "--scoring-view", str(view)]
    if resume:
        command.append("--resume")
    run_command(command)
    register(study, f"{stage}/{domain}/{condition}/predictions", output / "predictions.jsonl")
    if domain == "tennis":
        register(study, f"{stage}/{domain}/{condition}/primary", output / "primary_predictions.jsonl")
    return str(output)


def retention_gate(study):
    study = Path(study)
    verify(study)
    a = artifact(study, "selection/tiser/C0/predictions")
    b = artifact(study, "selection/tiser/C1/predictions")
    spec = {"seed": 42, "replicates": 10000, "comparisons": [{"id": "C1-C0", "domain": "tiser", "baseline": str(a), "candidate": str(b)}]}
    path = study / "selection_statistics_spec.json"
    freeze(path, spec)
    output = study / "selection_statistics"
    result = read(output / "statistics.json") if (output / "statistics.json").exists() else analyze_spec(path, output)
    comparison = result["comparisons"]["C1-C0"]
    decision = {"decision": comparison["decision"], "em": comparison["em"], "statistics_sha256": sha256(output / "statistics.json")}
    freeze(study / "forgetting_gate.json", decision)
    register(study, "forgetting_gate", study / "forgetting_gate.json")
    return decision


def require_replay(study):
    if (Path(study) / "final_campaign.json").exists():
        raise ValueError("Training is closed after final campaign freeze")
    gate = read(artifact(study, "forgetting_gate"))
    if gate["decision"] != "clear_forgetting":
        raise ValueError("The forgetting gate does not authorize replay training")


def build_replay(study):
    from transformers import AutoTokenizer
    from src.data.dataset import _encode_train_example
    study = Path(study)
    verify(study)
    require_replay(study)
    provenance = read(artifact(study, "original_data_source"))
    train_path = resolve_reference(study, provenance["local_train"])
    test_path = resolve_reference(study, provenance["local_test"])
    for path in (train_path, test_path):
        if sha256(path) != provenance["files"][path.name]["sha256"]:
            raise ValueError("Original data changed")
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct", revision=model_revision(study))
    eligible = lambda r: len(_encode_train_example(r["prompt"], r["output"], tokenizer)["input_ids"]) <= 2048
    tennis = read(ROOT / "data/tennis/tennis_train_traced_full.json")
    if any(not eligible(r) for r in tennis):
        raise ValueError("Historical tennis rows fail the frozen tokenizer length filter")
    evals = read(artifact(study, "original_test_canonical")) + read(ROOT / "data/tennis/tennis_dev.json") + read(ROOT / "data/tennis/tennis_test.json")
    mixed, summary = replay_rows(tennis, _load_records(str(train_path)), evals, eligible=eligible)
    path = study / "data" / "replay_r25.json"
    freeze(path, mixed)
    freeze(study / "data" / "replay_summary.json", summary)
    register(study, "replay_data", path)
    return summary


def token_decision(study):
    study = Path(study)
    verify(study)
    require_replay(study)
    a = read(artifact(study, "training/C1R/exposure"))["supervised_tokens"]
    b = read(artifact(study, "training/R25/exposure"))["supervised_tokens"]
    result = token_gate(a, b)
    freeze(study / "token_gate.json", result)
    register(study, "token_gate", study / "token_gate.json")
    if result["sensitivity_required"]:
        metadata = read(artifact(study, "training/R25/population"))["accepted"]
        plan = closest_token_steps(metadata, a)
        freeze(study / "token_plan.json", plan)
        register(study, "token_plan", study / "token_plan.json")
        result = {**result, "plan": plan}
    return result


def _has_complete_adapter(adapter):
    adapter = Path(adapter)
    weights = (adapter / "adapter_model.safetensors").is_file() or (adapter / "adapter_model.bin").is_file()
    return weights and all((adapter / name).is_file() for name in
                           ("token_exposure.json", "training_spec.json", "train_metrics.json", "trainer_state.json"))


def archive_incomplete_training(study, condition):
    """Move an interrupted pre-checkpoint attempt aside without deleting evidence."""
    study = Path(study)
    run = study / "training" / condition
    model = study / "models" / condition
    adapter = model / "adapter"
    if _has_complete_adapter(adapter):
        raise ValueError("Training output appears complete; rerun without --restart-incomplete to recover it")
    present = [path for path in (run, model) if path.exists()]
    if not present:
        return None
    base = study / "failed_attempts" / condition
    attempt = base / f"attempt-{1 + len(list(base.glob('attempt-*'))):03d}"
    attempt.mkdir(parents=True, exist_ok=False)
    moved = {}
    for label, path in (("training", run), ("model", model)):
        if path.exists():
            target = attempt / label
            shutil.move(str(path), target)
            moved[label] = str(target.resolve())
    record = {"condition": condition, "archived_at": now(), "archive": str(attempt.resolve()), "moved": moved,
              "reason": "explicit restart of an incomplete attempt with no usable complete checkpoint"}
    append(study / "failed_attempts.jsonl", record)
    return record


def _register_training_outputs(study, registry, condition, cfg):
    adapter = Path(study) / "models" / condition / "adapter"
    run = Path(study) / "training" / condition
    if not _has_complete_adapter(adapter):
        raise ValueError(f"Training did not produce a complete adapter: {condition}")
    exposure = read(adapter / "token_exposure.json")
    population = read(run / "training_population.json")
    spec = read(adapter / "training_spec.json")
    expected_config = json.loads(json.dumps(cfg))
    expected_config["train"].pop("resume_from_checkpoint", None)
    if spec.get("config") != expected_config or spec.get("train_sha256") != sha256(cfg.paths.train_file):
        raise ValueError("Completed training inputs/configuration differ from the frozen condition")
    if read(run / "token_exposure.json") != exposure:
        raise ValueError("Run and adapter token ledgers differ")
    if exposure.get("optimizer_steps") != cfg.train.max_steps:
        raise ValueError("Completed optimizer-step count differs from the frozen condition")
    if len(population.get("accepted", [])) != cfg.train.expected_train_count:
        raise ValueError("Recorded training population differs from the frozen condition")
    if spec.get("source_sha256") != registry["source_sha256"]:
        raise ValueError("Training source snapshot differs from the study")
    if spec.get("starting_adapter", {}).get("sha256") != registry["conditions"]["C0"]["sha256"]:
        raise ValueError("Training did not start from the frozen C0 adapter")
    for previous in ("C1R", "R25", "R25-T"):
        if previous == condition or previous not in registry["conditions"]:
            continue
        prior_adapter = condition_adapter(study, registry["conditions"][previous])
        prior = read(prior_adapter / "training_spec.json")
        for key in ("environment", "hardware"):
            if prior.get(key) != spec.get(key):
                raise ValueError(f"{condition} and {previous} used different {key}")
        if prior["config"]["model"].get("revision") != spec["config"]["model"].get("revision"):
            raise ValueError("Contemporary training conditions used different model revisions")
    registry["conditions"][condition] = {"adapter": path_reference(study, adapter),
                                         "sha256": tree_hash(adapter)["sha256"]}
    write(Path(study) / "registry.json", registry)
    register(study, f"training/{condition}/exposure", adapter / "token_exposure.json")
    register(study, f"training/{condition}/population", run / "training_population.json")
    register(study, f"training/{condition}/spec", adapter / "training_spec.json")
    register(study, f"training/{condition}/run_meta", run / "run_meta.json")
    return registry["conditions"][condition]


def train_condition(study, condition, resume_checkpoint=None, restart_incomplete=False):
    study = Path(study)
    registry = verify(study)
    require_replay(study)
    if condition not in {"C1R", "R25", "R25-T"}:
        raise ValueError("Only C1R/R25/R25-T training is in scope")
    if condition in registry["conditions"]:
        raise ValueError("This condition is already trained and frozen")
    if resume_checkpoint and restart_incomplete:
        raise ValueError("Resume and restart-incomplete are mutually exclusive")
    if restart_incomplete:
        archive_incomplete_training(study, condition)
    cfg = load_config(str(ROOT / "config/config_tennis_7b_reported_best.yaml"))
    cfg.run_name = condition
    cfg.model.base_adapter = str(ROOT / C0)
    cfg.model.revision = model_revision(study)
    cfg.model.tokenizer_revision = cfg.model.revision
    cfg.train.update({"max_steps": 74, "fixed_schedule": True, "save_strategy": "steps", "save_steps": 25,
                       "expected_train_count": 600 if condition == "C1R" else 800})
    if condition == "R25-T":
        if not read(artifact(study, "token_gate"))["sensitivity_required"]:
            raise ValueError("Token mismatch does not trigger a sensitivity run")
        cfg.train.max_steps = read(artifact(study, "token_plan"))["max_steps"]
    cfg.paths.train_file = str(ROOT / "data/tennis/tennis_train_traced_full.json") if condition == "C1R" else str(artifact(study, "replay_data"))
    cfg.paths.output_dir, cfg.paths.model_dir = str(study / "training"), str(study / "models")
    path = save_config(study / "configs" / f"train_{condition}.yaml", cfg)
    from src.experiment.evaluation import environment, hardware
    for previous in ("C1R", "R25", "R25-T"):
        if previous not in registry["conditions"]:
            continue
        prior = read(condition_adapter(study, registry["conditions"][previous]) / "training_spec.json")
        if prior.get("environment") != environment() or prior.get("hardware") != hardware():
            raise ValueError(f"Current runtime does not match the contemporary {previous} training environment")
    if _has_complete_adapter(study / "models" / condition / "adapter"):
        return _register_training_outputs(study, registry, condition, cfg)
    command = ["scripts/tennis/train_tennis.py", "--config", str(path)]
    if resume_checkpoint:
        command += ["--resume-from-checkpoint", resume_checkpoint]
    run_command(command)
    return _register_training_outputs(study, registry, condition, cfg)


def freeze_final(study, audit_dir):
    study, audit_dir = Path(study), Path(audit_dir)
    registry = verify(study)
    gate = read(artifact(study, "forgetting_gate"))
    expected = ["C0", "C1"]
    if gate["decision"] == "clear_forgetting":
        expected += ["C1R", "R25"]
        if read(artifact(study, "token_gate"))["sensitivity_required"]:
            expected += ["R25-T"]
    if set(registry["conditions"]) != set(expected):
        raise ValueError("The preregistered training branch is incomplete")
    from src.audit import offline as audit
    from src.experiment.evaluation import validate_tennis_view
    summary = audit.summarize(audit_dir)
    if summary["status"] != "complete" or summary["completed"] != summary["expected"]:
        raise ValueError("Audit judgments/adjudication must be complete before final campaign")
    audit.freeze_views(audit_dir)
    for split in ("dev", "test"):
        rows = read(ROOT / f"data/tennis/tennis_{split}.json")
        validate_tennis_view(audit_dir / f"views/tennis_{split}.json", rows,
                             ROOT / f"data/tennis/tennis_{split}.json", gold_key="answer")
    if len(read(ROOT / "data/tennis/tennis_dev.json")) != 113:
        raise ValueError("Frozen final tennis population is not the expected 113 records")
    paths = [artifact(study, "retention_final"), artifact(study, "retention_selection"),
             audit_dir / "summary.json", audit_dir / "decisions.json",
             audit_dir / "views/tennis_dev.json", audit_dir / "views/tennis_test.json", artifact(study, "model_revision")]
    for condition in expected:
        for domain in ("tennis", "tiser"):
            paths.append(artifact(study, f"selection/{domain}/{condition}/" + ("primary" if domain == "tennis" else "predictions")))
    value = {"conditions": expected, "source_sha256": registry["source_sha256"],
             "protocol_sha256": registry["protocol_sha256"],
             "artifact_hashes": [{"reference": path_reference(study, p), "sha256": sha256(p)} for p in paths],
             "tennis_input_sha256": sha256(ROOT / "data/tennis/tennis_dev.json"),
             "tennis_original_n": 113, "allow_selection_after_freeze": False,
             "prior_113_use": read(study / "protocol.json")["prior_113_use"]}
    freeze(study / "final_campaign.json", value)
    register(study, "final_campaign", study / "final_campaign.json")
    return value


def final_statistics(study):
    study = Path(study)
    verify(study)
    campaign = read(artifact(study, "final_campaign"))
    conditions = campaign["conditions"]
    comparisons = []
    pairs = [("C0", "C1", "tiser"), ("C0", "C1", "tennis")]
    if "R25" in conditions:
        pairs += [("C0", "C1R", "tiser"), ("C1R", "R25", "tiser"), ("C1R", "R25", "tennis")]
    if "R25-T" in conditions:
        pairs += [("C1R", "R25-T", "tiser"), ("C1R", "R25-T", "tennis")]
    for a, b, domain in pairs:
        suffix = "primary" if domain == "tennis" else "predictions"
        comparisons.append({"id": f"{b}-{a}_{domain}", "domain": domain,
                            "baseline": str(artifact(study, f"final/{domain}/{a}/{suffix}")),
                            "candidate": str(artifact(study, f"final/{domain}/{b}/{suffix}"))})
    path = study / "final_statistics_spec.json"
    freeze(path, {"seed": 42, "replicates": 10000, "comparisons": comparisons})
    result_path = study / "final_statistics/statistics.json"
    if result_path.exists():
        result = read(result_path)
        if result.get("spec_sha256") != sha256(path):
            raise ValueError("Existing final statistics do not match the frozen specification")
    else:
        result = analyze_spec(path, study / "final_statistics")
    register(study, "final_statistics", study / "final_statistics/statistics.json")
    registry = read(study / "registry.json")
    registry["status"] = "complete"
    write(study / "registry.json", registry)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["init", "prepare-data", "evaluate", "gate", "replay-data", "train", "token-gate", "freeze-final", "statistics", "status"])
    p.add_argument("--study-dir", default=str(DEFAULT_STUDY))
    p.add_argument("--audit-dir", default=str(ROOT / "results/project_audit_v1"))
    p.add_argument("--train-file", default=str(ROOT / "data/TISER_train.json"))
    p.add_argument("--test-file", default=str(ROOT / "data/TISER_test.json"))
    p.add_argument("--source-manifest", default=str(ROOT / "data/TISER_source.json"))
    p.add_argument("--condition", choices=["C0", "C1", "C1R", "R25", "R25-T"])
    p.add_argument("--domain", choices=["tennis", "tiser"])
    p.add_argument("--stage", choices=["selection", "final"], default="selection")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--resume-from-checkpoint")
    p.add_argument("--restart-incomplete", action="store_true")
    args = p.parse_args(argv)
    study = Path(args.study_dir).resolve()
    if args.command in {"train", "evaluate"} and not args.condition:
        p.error("--condition is required")
    if args.command == "evaluate" and not args.domain:
        p.error("evaluate requires --domain")
    calls = {
        "init": lambda: initialize(study),
        "prepare-data": lambda: prepare_data(study, args.train_file, args.test_file, args.source_manifest),
        "evaluate": lambda: eval_condition(study, args.condition, args.domain, args.stage, audit_dir=args.audit_dir, resume=args.resume),
        "gate": lambda: retention_gate(study), "replay-data": lambda: build_replay(study),
        "train": lambda: train_condition(study, args.condition, args.resume_from_checkpoint, args.restart_incomplete),
        "token-gate": lambda: token_decision(study), "freeze-final": lambda: freeze_final(study, args.audit_dir),
        "statistics": lambda: final_statistics(study), "status": lambda: read(study / "registry.json"),
    }
    print(json.dumps(calls[args.command](), indent=2))
