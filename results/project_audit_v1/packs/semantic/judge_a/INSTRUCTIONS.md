# Isolated audit task

Read only the assigned batch JSON files and this guide. Do not inspect the parent
project, other judge passes, audit mappings, previous findings, or performance
results. Never use scripts, regex rules, lexical heuristics, or a blanket default
to assign semantic labels. Read and judge every item individually. Code may only
assemble, serialize, and check your already-made item-specific judgments.

Assign ONE batch per fresh task. Read every item in that batch; do not scan the
whole corpus or preclassify it with code. Write one response JSON into the assigned
response directory, named BATCH_ID.json. Preserve complete responses. Each file:
{"batch_id":"...", "batch_sha256":"...", "pass":"judge_a or judge_b or adjudicator",
 "judged_at":"ISO UTC timestamp", "observed_model_label":"label actually available, or unknown",
 "reasoning_effort":"high", "judgments":[
 {"audit_id":"...", "source_sha256":"...", "label":"...",
  "corrected_answer":null, "mention_kind":"none",
  "evidence":[{"field":"context or trace or reflection", "quote":"exact substring"}],
  "rationale":"brief item-specific explanation"}]}

Copy batch metadata and source_sha256 exactly. Include every item exactly once.
For reflection positives, use a nonempty exact reflection quote and an appropriate
mention_kind (memory_context_mismatch, contradiction_or_inconsistency,
uncertainty_or_doubt, other). Negative reflections require empty evidence and
mention_kind none. For semantic/trace labels mention_kind is always none; provide
at least one source quote except for unscorable. corrected_answer is a nonempty
string ONLY for semantic wrong_gold. If a judgment remains uncertain, state why
using the appropriate ambiguity/unscorable label. Never invent model snapshots,
provider response IDs, token usage, or exact settings unavailable in the UI.

Separate fresh tasks handle A and B. Adjudication tasks receive only their source
items and the two decisions to resolve. A task may stop at a batch boundary and
resume remaining batches; do not overwrite existing response files.
