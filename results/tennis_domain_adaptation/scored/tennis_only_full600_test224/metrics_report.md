# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 224
- Exact Match: 0.4643
- Token F1: 0.5164
- Malformed outputs: 0 (0.0000)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 29 | 0.3793 | 0.3793 | 0 | 0.0000 |
| `immediate_before_after` | 39 | 0.2308 | 0.4410 | 0 | 0.0000 |
| `other_temporal` | 3 | 0.6667 | 0.8889 | 0 | 0.0000 |
| `overlap_while_during` | 23 | 0.7391 | 0.7391 | 0 | 0.0000 |
| `tennis_injury_or_medical` | 1 | 0.0000 | 0.0000 | 0 | 0.0000 |
| `tournament_round_sequence` | 4 | 0.7500 | 0.8214 | 0 | 0.0000 |
| `which_first_last` | 47 | 0.4681 | 0.5218 | 0 | 0.0000 |
| `yes_no_before_after` | 78 | 0.5128 | 0.5128 | 0 | 0.0000 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 27 |
| `duration_minutes` | `number` | 1 |
| `duration_minutes` | `span` | 1 |
| `span` | `number` | 2 |
| `span` | `span` | 77 |
| `span` | `yes_no` | 12 |
| `tournament_round` | `tournament_round` | 3 |
| `yes_no` | `yes_no` | 101 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 27 |
| `duration_minutes` | `duration_minutes` | `number` | 1 |
| `duration_minutes` | `duration_minutes` | `span` | 1 |
| `immediate_before_after` | `span` | `span` | 39 |
| `other_temporal` | `span` | `number` | 1 |
| `other_temporal` | `span` | `span` | 1 |
| `other_temporal` | `tournament_round` | `tournament_round` | 1 |
| `overlap_while_during` | `span` | `span` | 1 |
| `overlap_while_during` | `yes_no` | `yes_no` | 22 |
| `tennis_injury_or_medical` | `span` | `number` | 1 |
| `tournament_round_sequence` | `span` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `tournament_round` | 2 |
| `tournament_round_sequence` | `yes_no` | `yes_no` | 1 |
| `which_first_last` | `span` | `span` | 35 |
| `which_first_last` | `span` | `yes_no` | 12 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 78 |

## Malformed Examples

No malformed outputs were detected.

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
