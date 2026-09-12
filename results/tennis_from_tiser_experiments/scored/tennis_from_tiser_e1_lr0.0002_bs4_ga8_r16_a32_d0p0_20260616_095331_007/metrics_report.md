# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 224
- Exact Match: 0.6071
- Token F1: 0.7408
- Malformed outputs: 0 (0.0000)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 29 | 0.4828 | 0.5057 | 0 | 0.0000 |
| `immediate_before_after` | 39 | 0.1282 | 0.6406 | 0 | 0.0000 |
| `other_temporal` | 3 | 0.3333 | 0.6778 | 0 | 0.0000 |
| `overlap_while_during` | 23 | 0.8696 | 0.8696 | 0 | 0.0000 |
| `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0 | 0.0000 |
| `tournament_round_sequence` | 4 | 0.7500 | 0.8611 | 0 | 0.0000 |
| `which_first_last` | 47 | 0.4681 | 0.6274 | 0 | 0.0000 |
| `yes_no_before_after` | 78 | 0.9103 | 0.9103 | 0 | 0.0000 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 22 |
| `duration_minutes` | `number` | 1 |
| `duration_minutes` | `span` | 6 |
| `span` | `span` | 83 |
| `span` | `yes_no` | 8 |
| `tournament_round` | `tournament_round` | 3 |
| `yes_no` | `yes_no` | 101 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 22 |
| `duration_minutes` | `duration_minutes` | `number` | 1 |
| `duration_minutes` | `duration_minutes` | `span` | 6 |
| `immediate_before_after` | `span` | `span` | 39 |
| `other_temporal` | `span` | `span` | 2 |
| `other_temporal` | `tournament_round` | `tournament_round` | 1 |
| `overlap_while_during` | `span` | `span` | 1 |
| `overlap_while_during` | `yes_no` | `yes_no` | 22 |
| `tennis_injury_or_medical` | `span` | `span` | 1 |
| `tournament_round_sequence` | `span` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `tournament_round` | 2 |
| `tournament_round_sequence` | `yes_no` | `yes_no` | 1 |
| `which_first_last` | `span` | `span` | 39 |
| `which_first_last` | `span` | `yes_no` | 8 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 78 |

## Malformed Examples

No malformed outputs were detected.

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
