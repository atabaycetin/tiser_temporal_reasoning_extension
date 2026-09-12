# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 224
- Exact Match: 0.3795
- Token F1: 0.4717
- Malformed outputs: 0 (0.0000)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 29 | 0.3448 | 0.3448 | 0 | 0.0000 |
| `immediate_before_after` | 39 | 0.1026 | 0.4420 | 0 | 0.0000 |
| `other_temporal` | 3 | 0.0000 | 0.4444 | 0 | 0.0000 |
| `overlap_while_during` | 23 | 0.6522 | 0.6947 | 0 | 0.0000 |
| `tennis_injury_or_medical` | 1 | 0.0000 | 0.0000 | 0 | 0.0000 |
| `tournament_round_sequence` | 4 | 0.5000 | 0.5417 | 0 | 0.0000 |
| `which_first_last` | 47 | 0.1702 | 0.2753 | 0 | 0.0000 |
| `yes_no_before_after` | 78 | 0.5897 | 0.5897 | 0 | 0.0000 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 7 |
| `duration_minutes` | `number` | 21 |
| `duration_minutes` | `span` | 1 |
| `span` | `number` | 2 |
| `span` | `span` | 89 |
| `tournament_round` | `tournament_round` | 3 |
| `yes_no` | `span` | 5 |
| `yes_no` | `yes_no` | 96 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 7 |
| `duration_minutes` | `duration_minutes` | `number` | 21 |
| `duration_minutes` | `duration_minutes` | `span` | 1 |
| `immediate_before_after` | `span` | `span` | 39 |
| `other_temporal` | `span` | `number` | 1 |
| `other_temporal` | `span` | `span` | 1 |
| `other_temporal` | `tournament_round` | `tournament_round` | 1 |
| `overlap_while_during` | `span` | `span` | 1 |
| `overlap_while_during` | `yes_no` | `span` | 5 |
| `overlap_while_during` | `yes_no` | `yes_no` | 17 |
| `tennis_injury_or_medical` | `span` | `number` | 1 |
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
