# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 113
- Exact Match: 0.5752
- Token F1: 0.6770
- Malformed outputs: 0 (0.0000)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 15 | 0.4667 | 0.4667 | 0 | 0.0000 |
| `immediate_before_after` | 20 | 0.2500 | 0.6256 | 0 | 0.0000 |
| `other_temporal` | 2 | 0.5000 | 0.5000 | 0 | 0.0000 |
| `overlap_while_during` | 11 | 0.9091 | 0.9091 | 0 | 0.0000 |
| `tennis_injury_or_medical` | 1 | 0.0000 | 0.6667 | 0 | 0.0000 |
| `tournament_round_sequence` | 2 | 0.5000 | 0.5000 | 0 | 0.0000 |
| `which_first_last` | 23 | 0.3913 | 0.5356 | 0 | 0.0000 |
| `yes_no_before_after` | 39 | 0.8205 | 0.8205 | 0 | 0.0000 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 4 |
| `duration_minutes` | `number` | 10 |
| `duration_minutes` | `span` | 1 |
| `number` | `span` | 1 |
| `span` | `span` | 43 |
| `span` | `yes_no` | 2 |
| `tournament_round` | `span` | 1 |
| `tournament_round` | `tournament_round` | 1 |
| `yes_no` | `yes_no` | 50 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 4 |
| `duration_minutes` | `duration_minutes` | `number` | 10 |
| `duration_minutes` | `duration_minutes` | `span` | 1 |
| `immediate_before_after` | `span` | `span` | 20 |
| `other_temporal` | `number` | `span` | 1 |
| `other_temporal` | `tournament_round` | `tournament_round` | 1 |
| `overlap_while_during` | `yes_no` | `yes_no` | 11 |
| `tennis_injury_or_medical` | `span` | `span` | 1 |
| `tournament_round_sequence` | `span` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `span` | 1 |
| `which_first_last` | `span` | `span` | 21 |
| `which_first_last` | `span` | `yes_no` | 2 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 39 |

## Malformed Examples

No malformed outputs were detected.

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
