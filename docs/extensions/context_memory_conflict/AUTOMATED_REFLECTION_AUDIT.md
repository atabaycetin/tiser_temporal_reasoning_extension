# Fully Automated Reflection-Conflict Audit

> **Legacy API alternative, not the active project audit.** The approved study
> uses isolated GPT-5.6 Sol Codex file batches with no API calls. Its exact procedure
> is [`docs/REFLECTION_AUDIT_RUNBOOK.md`](../../REFLECTION_AUDIT_RUNBOOK.md), and
> its evidence lives under `results/reflection_audit/`. Do not combine results
> from this API workflow with that study or use an API snapshot name as evidence
> for the model behind a Codex UI task.

## Purpose and limitation

This protocol replaces the unavailable historical Claude workflow with a new,
fully automated, auditable model-as-judge run. It answers one narrow question:

> Does the text inside `<reflection>` explicitly acknowledge a mismatch between
> supplied context and remembered, expected, or generally known information?

It does not require team members or manual labels. It also cannot prove that its
own labels are error-free. Two blinded judge passes and automatic adjudication
reduce run-to-run instability, but both passes can share model bias. The new
result must therefore be labelled an automated GPT-5.6 Sol audit, not a reproduction
of the missing historical Claude result.

The implementation is
[`scripts/conflict/audit_reflections_openai.py`](../../../scripts/conflict/audit_reflections_openai.py).
It uses [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
so every provider response conforms to a fixed JSON schema. It sends only a pseudonymous ID and reflection text; model
condition, conflict class, expected answers, and correctness are joined back
after judging.

## Prerequisites

1. Run commands from the repository root.
2. Use Python 3.10 or newer.
3. Ensure the committed scored files exist:
   - `results/context_memory_conflict/scored/base__tiser.jsonl`
   - `results/context_memory_conflict/scored/tiser__tiser.jsonl`
4. Obtain an OpenAI Platform API key with access to the requested model. The
   script does not use a ChatGPT browser session and never writes the key to an
   artifact.
5. Keep the model identifier fixed. The default is the documented
   [GPT-5.6 Sol model](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
   `gpt-5.6-sol`.

## Exact procedure

### Step 1: freeze and automatically validate blinded requests without API calls

```bash
python3 scripts/conflict/audit_reflections_openai.py \
  --prepare-only \
  --output-dir outputs/reflection_audit_preview
```

This writes the exact prompt, JSON schema, input and request hashes, immutable
run specification, and blinded request payloads. It fails on malformed source
JSON and completes without a model call; no manual labelling or request review
is required. No result is produced and no network request is made. Choose a new
preview directory, or pass `--force` if you intentionally want to replace only
that disposable preview.

### Step 2: expose the API key only to the current shell

```bash
read -s OPENAI_API_KEY
export OPENAI_API_KEY
```

Paste the key when prompted and press Enter. Do not place the key in a config,
notebook, command argument, Git-tracked file, or report.

### Step 3: run the complete audit

```bash
python3 scripts/conflict/audit_reflections_openai.py \
  --model gpt-5.6-sol \
  --workers 4 \
  --output-dir results/context_memory_conflict/scored/audit_openai_v1
```

For every unique, structurally valid reflection the script automatically:

1. computes a SHA-256 identifier;
2. sends the reflection alone to conservative judge A;
3. sends the same reflection alone to independently worded judge B;
4. accepts their label when they agree;
5. sends disagreements to a third adjudicator;
6. requires an exact evidence substring for every positive label;
7. joins conflict metadata only after the final decision;
8. calculates genuine-conflict rate, control false-positive rate, Wilson 95%
   intervals, class-specific rates, judge disagreement, lexical-proxy confusion,
   and silent overrides among context-faithful answers; and
9. records input, prompt, model, Git, and output provenance.

The command may take time because it makes two calls per unique reflection and
additional calls for disagreements. Lower `--workers` if rate limits are hit.
The script retries transient transport errors with bounded exponential backoff
and automatically re-judges schema-valid responses whose positive evidence is
not an exact substring of the source reflection. Failed validation responses
are retained alongside the eventual valid response for cost and provenance
accounting.

### Step 4: resume safely after interruption

```bash
python3 scripts/conflict/audit_reflections_openai.py \
  --model gpt-5.6-sol \
  --workers 4 \
  --resume \
  --output-dir results/context_memory_conflict/scored/audit_openai_v1
```

Completed calls are read from `raw_responses.jsonl`; only missing jobs are sent.
The cache key is the reflection SHA-256 plus judge pass, and every cached record
must match the current request hash. The script also refuses to resume if the
model, prompt, source-file hashes, row limit, or primary payloads differ from the
frozen `run_spec.json`, so resumption is safe and does not depend on row order.

### Step 5: verify completion automatically

```bash
python3 -c "import csv,json,pathlib; p=pathlib.Path('results/context_memory_conflict/scored/audit_openai_v1'); s=json.loads((p/'summary.json').read_text()); assert set(s['cells'])=={'base__tiser','tiser__tiser'}; assert all(v['all_rows']==1176 for v in s['cells'].values()); assert all(v['unscorable']<=3 for v in s['cells'].values()); print(json.dumps(s['cells'], indent=2))"
```

This fails if either expected cell or its 1,176 source rows is missing. A small
number of unscorable rows is expected because the committed scored files record
one malformed TISER reflection and three malformed base reflections.

### Step 6: archive the complete evidence bundle

Keep all files in `audit_openai_v1/` together:

| Artifact | Role |
| --- | --- |
| `judge_prompt.txt` | Exact two-pass rubric, adjudicator rubric, and schema |
| `requests.jsonl` | Every blinded request payload |
| `run_spec.json` | Frozen input hashes, model, prompt version, limit, and request hashes |
| `raw_responses.jsonl` | Provider responses, IDs, model strings, and usage |
| `base__tiser.audit.csv` | Row-level base-model labels plus joined metadata |
| `tiser__tiser.audit.csv` | Row-level TISER-model labels plus joined metadata |
| `summary.json` | Rates, Wilson intervals, disagreements, and confusion counts |
| `run_meta.json` | Command, input hashes, prompt hash, Git state, and settings |

Commit the bundle only after checking that repository policy permits retaining
provider responses. The inputs are already public project artifacts and the
script stores no API key.

### Step 7: update the report without overstating the result

Use the `tiser__tiser` value under
`cells -> tiser__tiser -> genuine_conflicts` as the primary conflict-detection
estimate. Report its count, denominator, rate, and Wilson interval. Report the
control false-positive rate next to it. Replace the old 4.3% number only after
this run; do not average the new GPT value with the historical Claude value.

Suggested wording:

> GPT-5.6 Sol judged each persisted reflection twice under two
> conservative rubrics, with automatic adjudication of disagreements. The judge
> received no model identity, conflict class, gold answer, or correctness signal.
> Row-level requests, responses, labels, hashes, and Wilson intervals are retained.

Then give the measured values from `summary.json` and state that the audit has
no human-calibrated accuracy estimate.

## Optional smoke run

To verify the whole local preparation path on two rows per cell without using
the API:

```bash
python3 scripts/conflict/audit_reflections_openai.py \
  --prepare-only \
  --limit 2 \
  --output-dir outputs/reflection_audit_smoke
```

Do not report smoke-run values.
