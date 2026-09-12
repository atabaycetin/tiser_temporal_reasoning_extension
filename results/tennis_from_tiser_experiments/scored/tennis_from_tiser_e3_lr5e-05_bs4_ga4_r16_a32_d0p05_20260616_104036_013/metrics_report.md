# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 224
- Exact Match: 0.7098
- Token F1: 0.8381
- Malformed outputs: 0 (0.0000)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 29 | 0.6552 | 0.6782 | 0 | 0.0000 |
| `immediate_before_after` | 39 | 0.2051 | 0.6783 | 0 | 0.0000 |
| `other_temporal` | 3 | 0.3333 | 0.5370 | 0 | 0.0000 |
| `overlap_while_during` | 23 | 0.9565 | 0.9565 | 0 | 0.0000 |
| `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0 | 0.0000 |
| `tournament_round_sequence` | 4 | 0.7500 | 0.7500 | 0 | 0.0000 |
| `which_first_last` | 47 | 0.6596 | 0.8441 | 0 | 0.0000 |
| `yes_no_before_after` | 78 | 0.9615 | 0.9615 | 0 | 0.0000 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 25 |
| `duration_minutes` | `number` | 1 |
| `duration_minutes` | `span` | 3 |
| `span` | `span` | 91 |
| `tournament_round` | `tournament_round` | 3 |
| `yes_no` | `yes_no` | 101 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 25 |
| `duration_minutes` | `duration_minutes` | `number` | 1 |
| `duration_minutes` | `duration_minutes` | `span` | 3 |
| `immediate_before_after` | `span` | `span` | 39 |
| `other_temporal` | `span` | `span` | 2 |
| `other_temporal` | `tournament_round` | `tournament_round` | 1 |
| `overlap_while_during` | `span` | `span` | 1 |
| `overlap_while_during` | `yes_no` | `yes_no` | 22 |
| `tennis_injury_or_medical` | `span` | `span` | 1 |
| `tournament_round_sequence` | `span` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `tournament_round` | 2 |
| `tournament_round_sequence` | `yes_no` | `yes_no` | 1 |
| `which_first_last` | `span` | `span` | 47 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 78 |

## Malformed Examples

No malformed outputs were detected.

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
