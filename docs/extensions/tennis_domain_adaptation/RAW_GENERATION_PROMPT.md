# Raw Tennis-Example Generation Prompt

## Purpose

ChatGPT-5.5 used the following prompt to generate the 1,122 synthetic raw
tennis context/question/answer records. This is stage 1 of the data pipeline.
Stage 2 used the separate trace-generation prompt to transform training examples
and their supplied gold answers into supervised TISER traces.

## Generation prompt

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

You may use realistic player names such as Sinner, Alcaraz, Djokovic, Medvedev, Zverev, Rune, Rublev, Fritz, Nadal, Federer, Tsitsipas, Ruud, Shelton, De Minaur.

The events do NOT need to be historically true. Treat them as fictional but realistic tennis narratives.

CONTEXT REQUIREMENTS

Each context must:

- contain 3 to 6 sentences
- contain at least 3 temporal events
- be self-contained
- be unambiguous
- avoid external knowledge
- use natural sports-report language
- include clear temporal signals such as:
  - before
  - after
  - during
  - while
  - later
  - earlier
  - immediately after
  - at the same time
  - minutes later
  - in the first set
  - in the second set
  - before the tie-break
  - after the medical timeout

QUESTION REQUIREMENTS

Generate a balanced mix of question types:

1. Yes/No temporal comparison
Example:
"Did Sinner call the medical timeout before breaking serve?"

2. Which happened first?
Example:
"Which happened first: Alcaraz saved a break point or Medvedev won the tie-break?"

3. Which happened last?
Example:
"Which event happened last?"

4. What happened before X?
Example:
"What happened before the rain delay?"

5. What happened after X?
Example:
"What happened after Djokovic lost the second set?"

6. Duration / time gap
Example:
"How many minutes after the match started did the rain delay begin?"

7. During / overlap
Example:
"Was the roof being closed while the players were off court?"

8. Tournament progression
Example:
"Did Sinner reach the semifinal before playing the final?"

ANSWER REQUIREMENTS

Each answer must:

- be short
- be exact
- be unambiguous
- directly answer the question
- not include explanations

Use answer formats like:

- "Yes"
- "No"
- "Sinner broke serve"
- "The rain delay"
- "Alcaraz won the second set"
- "45 minutes"
- "The semifinal"

IMPORTANT BALANCE CONSTRAINTS

Among the 50 examples, approximately include:

- 15 Yes/No before-after questions
- 10 first/last ordering questions
- 8 what happened before/after questions
- 7 duration or time-gap questions
- 5 during/overlap questions
- 5 tournament progression questions

Difficulty distribution:

- 15 easy examples with direct before/after reasoning
- 25 medium examples with 3-4 ordered events
- 10 hard examples with 5-6 events or distractor events

QUALITY RULES

Avoid ambiguous cases such as:
- "in 2014" without month/day when asking about a specific month
- unclear transitions between teams, rounds, or sets
- answers that require real tennis knowledge
- questions with multiple valid answers
- contexts where two events could reasonably be interpreted in different orders

Do not repeat the same structure too many times.
Do not generate near-duplicate examples.
Do not always use the same players.
Do not always make the answer "Yes".
Use both positive and negative examples.

Before producing the final output, internally check each example:
- Is the answer derivable from the context?
- Is the temporal order clear?
- Is there only one correct answer?
- Is the answer short?
- Is the example about tennis?
- Did you avoid reasoning/timeline/reflection?

OUTPUT FORMAT

Return only a valid JSON array.

Example format:

[
  {
    "context": "Sinner held serve in the opening game. Djokovic called a medical timeout before Sinner broke serve in the fourth game. After the break of serve, rain delayed the match for twenty minutes.",
    "question": "Did Djokovic call the medical timeout before Sinner broke serve?",
    "answer": "Yes"
  },
  {
    "context": "Alcaraz saved two break points at 2-3 in the first set. Medvedev broke serve three games later. The set ended with Medvedev winning a tie-break.",
    "question": "Which happened first: Medvedev broke serve or Alcaraz saved two break points?",
    "answer": "Alcaraz saved two break points"
  }
]

Now generate exactly 50 examples.
```

## Dataset processing

The generated records were combined into the 1,122-record raw collection, then
schema-audited, categorised, converted to TISER-compatible inputs, and split
deterministically into 785 training, 113 development, and 224 test records.

See [`TRACE_GENERATION_PROMPT.md`](TRACE_GENERATION_PROMPT.md) for stage 2.
