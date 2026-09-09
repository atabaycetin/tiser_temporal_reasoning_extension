# Tennis Trace-Generation Prompt

## Purpose

ChatGPT-5.5 used the following prompt to generate supervised TISER traces from
the tennis training examples and their supplied gold answers.

This is stage 2 of the data pipeline. It is not the prompt that created the
original 1,122 raw examples. It asks
for `question_id` and `output`, assumes that a context and `gold_answer` have
already been provided, and transforms an existing supervised example into a
TISER trace. The stage-1 prompt is documented separately
in [`RAW_GENERATION_PROMPT.md`](RAW_GENERATION_PROMPT.md).

## Generation prompt

```text
You will receive tennis temporal reasoning training examples.

For each example, generate only one JSONL record with the following fields:

{
  "question_id": "...",
  "output": "..."
}

The output must follow the TISER format:

<reasoning>
...
<timeline>
...
</timeline>
<reflection>
...
</reflection>
...
</reasoning>
<answer>GOLD_ANSWER</answer>

Rules:
- Use only information contained in the provided context.
- Reason explicitly about the temporal relations required to answer the question.
- Construct a chronological timeline containing the relevant events.
- In the reflection, verify that the reasoning and timeline support the gold answer.
- Do not invent events, dates, entities, or temporal relations.
- The final answer must match the provided gold_answer exactly.
- Preserve the question_id exactly.
- Output one JSON object per line.
- Output JSONL only. Do not include markdown, explanations, headings, or any additional text.
```

## Artifact compatibility

The committed full-batch request rows contain `question_id`, `dataset_name`,
`category`, `context`, `question`, `gold_answer`, and a per-example `prompt`.
That per-example prompt independently requests the same nested reasoning,
timeline, reflection, and answer structure, use of context only, and exact gold
answer. Generated rows contain exactly `question_id` and `output`. The 600 IDs
are the ordered contents of batches 1--12.

This was supervised trace construction, not model evaluation: the gold answer
was part of the generation input.

## Repair history

The original full-generation backup has 593 physical lines from which 600
objects were recoverable. Nineteen malformed lines covered 26 objects. A total
of 200 outputs--all records in batches 3, 6, 9, and 12--lacked the requested
XML-like tags and were wrapped using their existing text plus the source gold
answer. Final validation confirms schema, tags, placeholders, and equality to
the supplied gold; it does not establish that the gold is entailed by the
context.

## Canonical prompt for future trace generation

The following tightened prompt addresses the failure modes observed above. It
is a recommendation for future runs and must not be labelled as the historical
prompt.

```text
You will receive one or more JSON objects. Each object contains:
- question_id
- context
- question
- gold_answer
- category

For every input object, output exactly one JSON object on exactly one physical
line, in the same order as the inputs:

{"question_id":"<EXACT_INPUT_ID>","output":"<reasoning>\n...\n<timeline>\n...\n</timeline>\n<reflection>\n...\n</reflection>\n</reasoning>\n<answer>EXACT_GOLD_ANSWER</answer>"}

Rules:
- Preserve question_id byte for byte.
- Use only information explicitly contained in context.
- Reason explicitly about the temporal relation needed for the question.
- Include only relevant events in chronological order in timeline.
- In reflection, verify that the reasoning and timeline support gold_answer.
- Do not invent facts, events, dates, entities, or temporal relations.
- Copy gold_answer exactly, including capitalization and punctuation.
- Include each required opening and closing tag exactly once.
- Nest timeline and reflection inside reasoning, as shown.
- JSON-escape all embedded newlines, quotation marks, and backslashes.
- Do not omit or duplicate any input record.
- Output JSONL only: no Markdown fences, headings, explanations, or blank lines.
```
