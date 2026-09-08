# Tennis Temporal-QA Dataset Card

## Summary

This directory contains a synthetic English temporal-question-answering
dataset built around professional-tennis narratives. Questions cover event
order, immediate succession, overlap, elapsed time, and tournament rounds.
The dataset supports the supervised tennis-domain-adaptation extension in this
repository; it is not intended as a factual record of tennis matches.

## Provenance

The available creation record, dated 2026-09-04, states that the 1,122 raw
context/question/answer records were created interactively with ChatGPT using
GPT-5.5. A recovered fragment of the raw-generation prompt is retained, but its
continuation, conversation export, complete generation history, decoding
settings, and exact model snapshot are unavailable. This provenance therefore
rests on recollection rather than independent verification from the committed
artifacts. No external source corpus is recorded. See
[`RAW_GENERATION_PROMPT.md`](../../docs/extensions/tennis_domain_adaptation/RAW_GENERATION_PROMPT.md).

The same creation record describes trace generation as a separate supervised
step using ChatGPT with GPT-5.5. Each committed request supplied the question
ID, category, context, question, and gold answer. The recovered batch
instruction is compatible with the artifacts but is not authenticated as the
exact literal prompt. See
[`TRACE_GENERATION_PROMPT.md`](../../docs/extensions/tennis_domain_adaptation/TRACE_GENERATION_PROMPT.md)
and [`PROVENANCE.json`](PROVENANCE.json).

## Composition and processing

| Artifact | Records | Purpose |
| --- | ---: | --- |
| `raw/tennis_raw.json` | 1,122 | Synthetic raw context/question/answer triples |
| `processed/tennis_all_tiser.json` | 1,122 | Converted TISER-compatible records |
| `tennis_train.json` | 785 | Canonical training pool and source for trace generation |
| `tennis_dev.json` | 113 | Development split, intended for model selection; never used for gradient updates |
| `tennis_test.json` | 224 | Common evaluation split; historically also used to rank 7B adapters |
| `tennis_train_traced_50.json` | 50 | Valid pilot traces for train positions 0--49; used only by smoke/pilot runs |
| `tennis_train_traced_full.json` | 600 | Traces for train positions 50--649; used by the reported adaptations |
| Trace-request batches 13--15 | 135 | Train positions 650--784; prompts prepared but no generated outputs |

The recorded pipeline validates the minimal schema, assigns stable IDs and
rule-based categories, detects duplicate-like records, creates prompts, and
performs a category-aware, duplicate-group-aware 70/10/20 split with seed 42.
The commands and expected outputs are documented in the repository README.

The historical `source: "unknown"` value inside converted records was retained
to preserve byte-level reproducibility of the reported artifacts. The external
provenance documents in this directory supersede that placeholder without
silently changing the data used by the reported models.

## Why the reported training file has 600 records

The three canonical splits are disjoint, their union is all 1,122 converted
records, and no exact duplicate crosses a split. Only training-split records
were eligible for trace generation and supervised adapter fitting. Development
and test records remain evaluation examples and were never supplied as
training targets.

The 600-record file is an operational cutoff, not a quality-filtered or
sample-efficiency-selected subset:

- the first 50 training records were processed as a pilot;
- prompts were then prepared for all 735 non-pilot records in fifteen batches;
- generated output exists for batches 1--12 only, giving 600 records;
- batches 13--15 contain 135 prepared but ungenerated requests; and
- the valid 50-record pilot was never concatenated into the 600-record file.

Thus the 185 training records absent from `tennis_train_traced_full.json` are
exactly the 50 traced pilot records plus the 135 genuinely ungenerated tail
records. The repository contains 650 unique traced training records overall,
but only the disjoint 600-record full-run artifact was used by the reported
adaptations. See the trace-coverage audit under
`results/tennis_domain_adaptation/trace_coverage/`.

The complete 785-record training split is retained deliberately. Deleting the
pilot would erase the provenance of the smoke experiments; deleting the tail
would make the canonical splits cease to cover all 1,122 records and would
break the prepared trace-generation manifest. Neither deletion changes what
the reported trainer reads, because its configuration already points directly
to the 600-record traced file. Any cleaned or expanded training set should be
published as a new, versioned derivative rather than silently replacing these
historical artifacts.

## Quality controls and limitations

The committed structural audit reports 1,122/1,122 schema-valid raw records,
one exact duplicate after its first occurrence, and eight near-duplicate
records after their first match. Structural validation does **not** establish
that a question has one answer entailed by its context.

A targeted, reproducible, AI-assisted review covered 302/785 training records,
including all duration and overlap questions, every pilot record, stratified
coverage of traced and untraced records, and additional temporal-risk cases.
It flagged ten records whose gold answer is wrong or not uniquely entailed:
seven are inside the reported 600 and three are in the ungenerated tail. This
confirms that semantic issues exist while disproving the hypothesis that they
explain the 600-record cutoff. The review was targeted rather than random; it
does not estimate the dataset-wide error rate or certify the other records.
See `results/tennis_domain_adaptation/semantic_audit/`.

For the 600 full-run traces, 200 outputs were mechanically wrapped to restore
missing TISER tags, and 26 records were recovered from 19 malformed physical
JSONL lines. All 600 then passed structural and gold-answer-equality checks.
Those repairs did not validate or correct semantic entailment.

Training a replacement final model should follow human adjudication of all
splits, a recorded keep/correct/remove decision for every reviewed item,
regeneration of affected traces, and reservation of a genuinely untouched
final evaluation set.

## License

The dataset is released under CC BY 4.0, subject to the scope and third-party
rights notice in [`DATASET_LICENSE.md`](DATASET_LICENSE.md).
