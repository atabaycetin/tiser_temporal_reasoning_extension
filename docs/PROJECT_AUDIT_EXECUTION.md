# Separate Offline Audit Workflows

The reflection, tennis semantic, and tennis trace audits are independent studies.
Each has its own frozen inputs, batches, accepted-response ledger, progress file,
adjudications, and summary. They use Codex file batches and make no API calls.
The exact click-by-click and command-by-command procedure for the reflection
study is in `docs/REFLECTION_AUDIT_RUNBOOK.md`; the reusable text pasted into
each Codex task is the entire contents of `docs/GPT56_SOL_AUDIT_TASK_PROMPT.md`.

The incomplete historical attempt under `results/project_audit_v1` remains
separate. Its judgments must not be relabelled or imported into these GPT-5.6 Sol
audits.

## 1. Reflection audit: replacement for the Claude aggregate

This is the only audit that replaces the unreproducible historical Claude
reflection result. It covers 2,295 unique scorable reflections, maps them back to
2,348 source rows, and adds four structurally unscorable rows to recover both
1,176-row model conditions.

```bash
python3 scripts/audit.py prepare --kind reflection \
  --output-dir results/reflection_audit \
  --requested-model gpt-5.6-sol
```

Run and import both passes, then adjudicate and summarize:

```bash
python3 scripts/audit.py import --output-dir results/reflection_audit \
  --response /absolute/path/to/BATCH_ID.json --task-id CODEX_TASK_ID
python3 scripts/audit.py adjudicate --output-dir results/reflection_audit
python3 scripts/audit.py summarize --output-dir results/reflection_audit
```

Completion of this directory produces the replacement reflection rates and the
two 1,176-row audit CSV files. It does not wait for either tennis audit.

## 2. Tennis semantic audit: evaluation labels

This study checks all 1,122 context/question/gold rows. There are 1,121 unique
payloads because `tennis_000406` and `tennis_000823` are identical; their shared
judgment maps back to both source IDs.

```bash
python3 scripts/audit.py prepare --kind semantic \
  --output-dir results/tennis_semantic_audit_v2 \
  --requested-model gpt-5.6-sol
python3 scripts/audit.py import --output-dir results/tennis_semantic_audit_v2 \
  --response /absolute/path/to/BATCH_ID.json --task-id CODEX_TASK_ID
python3 scripts/audit.py adjudicate --output-dir results/tennis_semantic_audit_v2
python3 scripts/audit.py summarize --output-dir results/tennis_semantic_audit_v2
python3 scripts/audit.py freeze-views --output-dir results/tennis_semantic_audit_v2
```

Only this audit creates the corrected 224-record selection and 113-record final
tennis scoring views used by the Colab experiment.

## 3. Tennis trace audit: training-data quality

This study checks the 50 pilot traces and 600 reported training traces. It
documents data quality and does not create evaluation labels or block the other
two audits.

```bash
python3 scripts/audit.py prepare --kind trace \
  --output-dir results/tennis_trace_audit_v2 \
  --requested-model gpt-5.6-sol
python3 scripts/audit.py import --output-dir results/tennis_trace_audit_v2 \
  --response /absolute/path/to/BATCH_ID.json --task-id CODEX_TASK_ID
python3 scripts/audit.py adjudicate --output-dir results/tennis_trace_audit_v2
python3 scripts/audit.py summarize --output-dir results/tennis_trace_audit_v2
```

## Running one complete judge pass

Judge A and Judge B must be separate fresh GPT-5.6 Sol tasks using high reasoning.
For strict blinding, use a projectless task and attach only that pass's combined
task-bundle JSON. Paste the complete frozen judge prompt from
`results/<audit-directory>/task_bundles/JUDGE_PROMPT.txt`. Do not give the task
access to the repository, mapping, other judge pass, prior decisions, or experiment results.
The task writes one response JSON per internal validation batch. Save those files
in one directory outside the audit directory and pass that directory to
`--response` to import the complete pass with one command.

The importer checks the response schema, timestamp, recorded model and reasoning
setting, batch and rubric hashes, pass identity, complete item coverage, source
hashes, labels, correction rules, rationales, and exact evidence substrings. A
response is accepted only when every item is valid. Original response bytes are
archived by hash, and the first valid judgment for each pass and item is retained.
The Codex UI model label remains operator-observed rather than independently
verified by the local script; preserve a unique task identifier with every import.

Run `adjudicate` after both passes. It produces batches for disagreements and for
every semantic `wrong_gold` proposal, even when the primary labels agree. Import
those responses and rerun `adjudicate` until no pending batch remains.

Each preparation records the relevant input hashes, frozen rubric and judge prompt,
requested model, and Git/source snapshot. Partial results are marked pending and
must not be reported as complete population estimates. No human calibration is
available, so shared model-judge bias remains a limitation.
