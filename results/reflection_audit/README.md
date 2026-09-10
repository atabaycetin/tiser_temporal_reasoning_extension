# GPT-5.6 Sol Reflection Audit

This directory contains the completed replacement audit for the reflection
outputs from the two TISER-prompt conditions in the Context--Memory Conflict
experiment. The audit replaces the historical Claude aggregate, whose exact
prompt, model version, and row-level decisions were not preserved.

## Completion status

- Unique scorable reflections: **2,295**
- Source rows represented by those reflections: **2,348**
- Structurally unscorable source rows: **4**
- Judge A decisions: **2,295**
- Judge B decisions: **2,295**
- Primary decisions in total: **4,590**
- Disagreements adjudicated: **66 of 66**
- Pending batches: **0**
- Final rows per model condition: **1,176**

`progress.json` and `summary.json` both record a completed audit.

## Main results

| Condition | Explicit conflict flags on genuine conflicts | Control false positives | Silent overrides among faithful answers |
| --- | ---: | ---: | ---: |
| Vanilla model + TISER prompt (`base__tiser`) | 87/1,053 = **8.26%** | 3/120 = **2.50%** | 543/554 = **98.01%** |
| TISER-trained model + TISER prompt (`tiser__tiser`) | 36/1,056 = **3.41%** | 3/119 = **2.52%** | 810/817 = **99.14%** |

The 95% Wilson intervals for genuine-conflict flagging are 6.75--10.08% for
`base__tiser` and 2.47--4.68% for `tiser__tiser`. In the TISER-trained condition,
the per-class rates are 4/203 (1.97%) for C1, 3/520 (0.58%) for C2, and 29/333
(8.71%) for C3. Explicit conflict detection therefore remains rare and is
concentrated in order-reversal conflicts.

The two judges disagreed on 66/2,295 unique reflections (2.88%). All disagreements
received an adjudicated decision. Human calibration was not performed, so shared
model-judge bias remains an explicit limitation.

## Directory contents

- `manifest.json`: frozen input hashes, model request, and preparation provenance.
- `task_protocol.json`: frozen judge protocol and prompt hash.
- `items.json`: 2,295 deduplicated reflection items supplied for judgment.
- `mapping.json`: private mapping from audit items back to source experiment rows.
- `malformed.json`: four source rows treated as structurally unscorable.
- `packs/`: individually hashed validation batches used by the importer.
- `task_bundles/`: complete Judge A, Judge B, and adjudicator input bundles, plus
  the exact judge prompt.
- `task_outputs/judge_a/`: 46 readable response files copied from the Judge A task.
- `task_outputs/judge_b/`: 46 readable response files copied from the Judge B task.
- `task_outputs/adjudicator/`: two readable adjudicator response files.
- `raw_responses/`: 94 canonical response copies named by their SHA-256 hashes.
- `accepted.jsonl`: accepted judgments linked to canonical response hashes.
- `import_log.jsonl`: validation result for every imported response file.
- `decisions.json`: final item-level decisions after adjudication.
- `base__tiser.audit.csv` and `tiser__tiser.audit.csv`: final row-level audit views.
- `summary.json`: aggregate rates, Wilson intervals, disagreement, and class results.
- `progress.json`: completion counters.
- `pending_batches.json`: empty list after all required judgments were accepted.

`task_outputs/` preserves human-readable filenames from the Codex tasks.
`raw_responses/` is the canonical evidence archive used by the validation code.
The original task-output files and their archived copies were verified as
byte-identical.

## Validation

From the repository root, run:

```bash
python3 scripts/audit.py summarize \
  --output-dir results/reflection_audit
```

Then verify the completion counters:

```bash
python3 -c "import json,pathlib; p=pathlib.Path('results/reflection_audit'); s=json.loads((p/'summary.json').read_text()); g=json.loads((p/'progress.json').read_text()); assert s['status']=='complete'; assert g['status']=='complete'; assert g['primary_completed']==4590; assert g['adjudications_required']==g['adjudications_completed']==66; assert json.loads((p/'pending_batches.json').read_text())==[]; assert s['completed']=={'reflection':2295}; assert all(s['reflection_cells'][c]['all_rows']==1176 for c in ('base__tiser','tiser__tiser')); print('Reflection audit validated successfully')"
```

Do not edit `raw_responses/`, `accepted.jsonl`, the frozen inputs, or batch files.
Any change to canonical response bytes breaks their content hashes and causes
validation to fail.
