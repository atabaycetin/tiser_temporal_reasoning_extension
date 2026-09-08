# Offline Project Audit Execution

This is the execution guide for the complete tennis semantic/trace audit and the
replacement reflection audit. It uses Codex file batches and makes no API calls.
The live source of truth is `results/project_audit_v1/progress.json`; partial
coverage is never published as a completed rate.

## Scope

The frozen audit contains:

| Kind | Unique judged items | Mapped source rows | Batch size |
| --- | ---: | ---: | ---: |
| Semantic context/question/gold | 1,121 | 1,122 | 25 |
| Training traces | 650 | 650 | 10 |
| Scorable reflections | 2,295 | 2,348 source-cell rows | 50 |

The two identical semantic training records share one blinded judgment and map
back to both source IDs. Four malformed/empty reflection rows bypass model
judgment and map to `unscorable`, yielding 1,176 rows in each of the two model
conditions after aggregation.

## Prepare and verify packs

```bash
python3 scripts/audit.py prepare --output-dir results/project_audit_v1
python3 scripts/audit.py summarize --output-dir results/project_audit_v1
```

Preparation freezes the seven input hashes, pseudonymous item payloads, private
mapping, malformed-row record, exact rubrics, exact task guide, and every batch.
The private `mapping.json` must never be given to a judge. A judge receives only
one `INSTRUCTIONS.md` and one assigned batch JSON.

Each A and B batch runs in a fresh isolated Codex task using the available
GPT-5.5 label with high reasoning effort. The UI label is recorded as observed
provenance; it does not prove an API snapshot or recover unavailable decoding
settings. Judges must read each item and may not use regexes, lexical rules,
scripts, or a blanket default to assign labels. Code may serialize and validate
decisions already made item by item.

## Import responses

```bash
python3 scripts/audit.py import \
  --output-dir results/project_audit_v1 \
  --response /absolute/path/to/BATCH_ID.json \
  --task-id CODEX_TASK_OR_BATCH_RUN_ID
```

The importer archives the original bytes by SHA-256 before validation. It then
checks the exact response schema, timezone-bearing timestamp, recorded high
reasoning effort, batch and rubric hashes, pass identity, complete/unique item
IDs, source hashes, allowed labels, correction rules, item-specific rationale,
and exact evidence substrings. A response is accepted only when every assigned
item is present and valid. The import is response-atomic: one missing or invalid
item leaves the entire batch pending, while the first judgment from a fully
valid response for each `(pass, audit_id)` is retained. All attempts remain in
`raw_responses/` and `import_log.jsonl`.

Known protocol violations belong in `quarantine.json`. Quarantined response
hashes can never enter the accepted journal. The preserved rejected regex-based
attempt is evidence of a failed attempt and contributes no judgments.

## Follow-ups and adjudication

```bash
python3 scripts/audit.py adjudicate --output-dir results/project_audit_v1
```

This regenerates `pending_batches.json` from accepted evidence. It exports fresh
A/B batches for missing or invalid items and adjudicator batches for every label
disagreement. Every semantic `wrong_gold` proposal is adjudicated even when A
and B agree, because a corrected evaluation label must have a separately
verified unique answer. Adjudicators receive only the source payload and the two
accepted decisions.

Import follow-up and adjudicator files through the same command, then rerun
`adjudicate` and `summarize`. Completion requires all 8,132 primary judgments
and every required adjudication.

## Publish derivatives

```bash
python3 scripts/audit.py summarize --output-dir results/project_audit_v1
python3 scripts/audit.py freeze-views --output-dir results/project_audit_v1
```

`freeze-views` refuses to run until semantic, trace, and reflection decisions
are all complete. It rechecks the original source hashes and produces immutable
sidecars for the 224-record selection set and 113-record final set. Supported
items and adjudicated unique corrections enter the primary scoring view;
underdetermined, inconsistent, and unscorable items remain in the original
input but are excluded from the primary denominator. Original gold labels are
retained for secondary historical scoring.

On completion, `summary.json` reports coverage by split/subset/category,
two-pass disagreement, reflection conflict rates, control false-positive rates,
Wilson intervals, unscorable counts, class breakdowns, lexical-proxy confusion,
and silent overrides. The two 1,176-row audit CSV files map final judgments back
to every original reflection row. The historical Claude aggregate remains a
separate historical claim. No human calibration exists, so shared model-judge
bias remains an explicit limitation.
