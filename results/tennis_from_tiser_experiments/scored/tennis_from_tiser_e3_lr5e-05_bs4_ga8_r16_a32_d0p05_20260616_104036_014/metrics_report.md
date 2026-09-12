# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 224
- Exact Match: 0.6205
- Token F1: 0.7523
- Malformed outputs: 0 (0.0000)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 29 | 0.5517 | 0.5747 | 0 | 0.0000 |
| `immediate_before_after` | 39 | 0.1538 | 0.6377 | 0 | 0.0000 |
| `other_temporal` | 3 | 0.3333 | 0.6778 | 0 | 0.0000 |
| `overlap_while_during` | 23 | 0.8696 | 0.8696 | 0 | 0.0000 |
| `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0 | 0.0000 |
| `tournament_round_sequence` | 4 | 0.5000 | 0.5000 | 0 | 0.0000 |
| `which_first_last` | 47 | 0.5106 | 0.6937 | 0 | 0.0000 |
| `yes_no_before_after` | 78 | 0.8974 | 0.8974 | 0 | 0.0000 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 20 |
| `duration_minutes` | `number` | 4 |
| `duration_minutes` | `span` | 5 |
| `span` | `span` | 88 |
| `span` | `yes_no` | 3 |
| `tournament_round` | `span` | 1 |
| `tournament_round` | `tournament_round` | 2 |
| `yes_no` | `yes_no` | 101 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 20 |
| `duration_minutes` | `duration_minutes` | `number` | 4 |
| `duration_minutes` | `duration_minutes` | `span` | 5 |
| `immediate_before_after` | `span` | `span` | 39 |
| `other_temporal` | `span` | `span` | 2 |
| `other_temporal` | `tournament_round` | `tournament_round` | 1 |
| `overlap_while_during` | `span` | `span` | 1 |
| `overlap_while_during` | `yes_no` | `yes_no` | 22 |
| `tennis_injury_or_medical` | `span` | `span` | 1 |
| `tournament_round_sequence` | `span` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `tournament_round` | 1 |
| `tournament_round_sequence` | `yes_no` | `yes_no` | 1 |
| `which_first_last` | `span` | `span` | 44 |
| `which_first_last` | `span` | `yes_no` | 3 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 78 |

## Malformed Examples

No malformed outputs were detected.

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
