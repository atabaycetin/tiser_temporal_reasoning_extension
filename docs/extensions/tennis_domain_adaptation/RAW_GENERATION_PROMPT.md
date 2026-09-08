# Raw Tennis-Example Generation Prompt Provenance

## Status

The following fragment was recovered from the 4 June 2026 ChatGPT conversation
used to create batches of synthetic raw tennis examples. The retained fragment
ends after `Nadal,`; the omitted continuation has not been reconstructed. This
document therefore distinguishes the recovered verbatim fragment from
constraints recalled or summarized afterward.

This is stage 1 of the data pipeline. It creates raw
`context`/`question`/`answer` triples. The separate trace-generation prompt is
stage 2 and converts existing triples into supervised TISER traces.

## Recovered verbatim fragment

```text
You are creating a synthetic domain-adaptation dataset for temporal reasoning in the professional tennis domain.
The dataset will be used to adapt a TISER-style temporal reasoning model. Your task is to generate RAW examples only.
For each example, output exactly one JSON object with these fields:
{
"context": "...",
"question": "...",
"answer": "..."
}
Do NOT generate reasoning.
Do NOT generate timeline.
Do NOT generate reflection.
Do NOT add explanations.
Do NOT wrap the output in markdown.
Do NOT use code fences.
Return a JSON array containing exactly 50 examples.
GENERAL GOAL
Each example must test temporal reasoning in tennis match or tournament narratives.
The model should need to reason about the order, overlap, duration, or sequence of events. The answer must be inferable only from the context.
DOMAIN
Use professional tennis scenarios such as:

- match progression
- first set, second set, third set
- breaks of serve
- service holds
- tie-breaks
- set points
- match points
- rain delays
- roof closure
- medical timeouts
- injury treatment
- warm-up interruptions
- tournament rounds
- quarterfinals, semifinals, finals
- player withdrawals
- comebacks
- coaching violations
- crowd interruptions
- changeovers
  You may use realistic player names such as Sinner, Alcaraz, Djokovic, Medvedev, Zverev, Rune, Rublev, Fritz, Nadal,
```

The recovered source cuts off at this point. Nothing after the final comma is
claimed to be a verbatim recovery.

## Additional recalled constraints, not verbatim

The available recollection indicates that the continuation also required:

- contexts of approximately three to six sentences;
- at least three temporal events per context;
- a balance of temporal question types;
- varied difficulty;
- an answer derivable from the supplied context; and
- a valid JSON array containing exactly 50 examples per request.

These points are recorded as a summary, not quoted text.

## Compatibility with the committed data

All 1,122 raw records have exactly the fields `context`, `question`, and
`answer`. Their contexts contain three to five sentences, and their tennis
vocabulary and temporal-question distribution are consistent with the
recovered instruction. This strongly corroborates the workflow but does not
authenticate the historical prompt character for character. The final count
of 1,122 is not divisible by 50, so the retained collection must reflect
aggregation, filtering, a partial final batch, or some combination of these;
the surviving artifacts do not distinguish which.

## Two-stage workflow

1. Raw generation: no existing example -> `context`, `question`, `answer`.
2. Trace generation: an existing raw example plus its gold answer -> TISER
   `reasoning`, `timeline`, `reflection`, and final `answer`.

See [`TRACE_GENERATION_PROMPT.md`](TRACE_GENERATION_PROMPT.md) for the recovered
stage-2 instruction and the trace-repair history.
