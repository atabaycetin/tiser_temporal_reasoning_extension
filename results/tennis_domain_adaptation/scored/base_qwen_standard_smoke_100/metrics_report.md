# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 100
- Exact Match: 0.3800
- Token F1: 0.4504
- Malformed outputs: 0 (0.0000)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 15 | 0.2000 | 0.2000 | 0 | 0.0000 |
| `immediate_before_after` | 15 | 0.1333 | 0.4784 | 0 | 0.0000 |
| `other_temporal` | 1 | 0.0000 | 0.0000 | 0 | 0.0000 |
| `overlap_while_during` | 7 | 0.5714 | 0.5714 | 0 | 0.0000 |
| `tournament_round_sequence` | 3 | 0.6667 | 0.7222 | 0 | 0.0000 |
| `which_first_last` | 15 | 0.0667 | 0.1798 | 0 | 0.0000 |
| `yes_no_before_after` | 44 | 0.5909 | 0.5909 | 0 | 0.0000 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 3 |
| `duration_minutes` | `number` | 12 |
| `span` | `span` | 31 |
| `tournament_round` | `tournament_round` | 3 |
| `yes_no` | `span` | 3 |
| `yes_no` | `yes_no` | 48 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 3 |
| `duration_minutes` | `duration_minutes` | `number` | 12 |
| `immediate_before_after` | `span` | `span` | 15 |
| `other_temporal` | `tournament_round` | `tournament_round` | 1 |
| `overlap_while_during` | `yes_no` | `span` | 3 |
| `overlap_while_during` | `yes_no` | `yes_no` | 4 |
| `tournament_round_sequence` | `span` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `tournament_round` | 2 |
| `which_first_last` | `span` | `span` | 15 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 44 |

## Malformed Examples

No malformed outputs were detected.

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
