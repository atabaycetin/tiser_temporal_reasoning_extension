# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 100
- Exact Match: 0.3300
- Token F1: 0.3767
- Malformed outputs: 1 (0.0100)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 15 | 0.3333 | 0.3778 | 0 | 0.0000 |
| `immediate_before_after` | 15 | 0.0667 | 0.2402 | 0 | 0.0000 |
| `other_temporal` | 1 | 0.0000 | 0.0000 | 0 | 0.0000 |
| `overlap_while_during` | 7 | 0.7143 | 0.7143 | 0 | 0.0000 |
| `tournament_round_sequence` | 3 | 0.3333 | 0.5952 | 0 | 0.0000 |
| `which_first_last` | 15 | 0.0667 | 0.1076 | 0 | 0.0000 |
| `yes_no_before_after` | 44 | 0.4545 | 0.4545 | 1 | 0.0227 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 1 |
| `duration_minutes` | `number` | 9 |
| `duration_minutes` | `span` | 5 |
| `span` | `span` | 22 |
| `span` | `yes_no` | 9 |
| `tournament_round` | `span` | 1 |
| `tournament_round` | `tournament_round` | 2 |
| `yes_no` | `empty` | 1 |
| `yes_no` | `yes_no` | 50 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 1 |
| `duration_minutes` | `duration_minutes` | `number` | 9 |
| `duration_minutes` | `duration_minutes` | `span` | 5 |
| `immediate_before_after` | `span` | `span` | 15 |
| `other_temporal` | `tournament_round` | `tournament_round` | 1 |
| `overlap_while_during` | `yes_no` | `yes_no` | 7 |
| `tournament_round_sequence` | `span` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `tournament_round` | 1 |
| `which_first_last` | `span` | `span` | 6 |
| `which_first_last` | `span` | `yes_no` | 9 |
| `yes_no_before_after` | `yes_no` | `empty` | 1 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 43 |

## Malformed Examples

| Question ID | Category | Gold | Predicted Answer |
| --- | --- | --- | --- |
| `tennis_000096` | `yes_no_before_after` | Yes |  |

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
