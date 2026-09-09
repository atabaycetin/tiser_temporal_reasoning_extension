# GPT-5.6 Sol Audit Task Prompt

Configure the Codex task to use **GPT-5.6 Sol** with **high** reasoning effort.
Give the task exactly one generated batch JSON and the adjacent
`INSTRUCTIONS.md`. Replace the two placeholders below and paste this prompt:

```text
Audit exactly the batch in <ABSOLUTE_BATCH_JSON_PATH>.

Follow <ABSOLUTE_INSTRUCTIONS_PATH> exactly. Treat the batch as the complete
source of evidence. Do not inspect the project, mappings, results, other judge
passes, or other batches. Read every item individually and make the audit
judgment yourself; do not use regexes, keyword rules, scripts, or a default
label to decide items.

Write one complete response JSON to <ABSOLUTE_RESPONSE_DIRECTORY>/<BATCH_ID>.json.
Use observed_model_label "gpt-5.6-sol" and reasoning_effort "high". Copy all
batch and item hashes exactly, include every item once, and quote evidence
exactly from the permitted source fields. Validate the response structure
before finishing.
```

Judge A and Judge B must run in separate fresh tasks. Run adjudicator batches
in another fresh GPT-5.6 Sol task. Import each response with:

```bash
python3 scripts/audit.py import \
  --output-dir results/project_audit_v2 \
  --response /absolute/path/to/BATCH_ID.json \
  --task-id CODEX_TASK_ID
```

The importer preserves the response and rejects incomplete batches, wrong
hashes, invalid labels, inexact evidence quotations, non-high reasoning, or a
model label other than `gpt-5.6-sol`.
