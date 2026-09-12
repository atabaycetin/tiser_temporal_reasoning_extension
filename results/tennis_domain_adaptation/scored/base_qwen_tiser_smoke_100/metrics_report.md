# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 100
- Exact Match: 0.3800
- Token F1: 0.4014
- Malformed outputs: 4 (0.0400)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 15 | 0.3333 | 0.3333 | 0 | 0.0000 |
| `immediate_before_after` | 15 | 0.0667 | 0.1792 | 0 | 0.0000 |
| `other_temporal` | 1 | 0.0000 | 0.0000 | 0 | 0.0000 |
| `overlap_while_during` | 7 | 0.7143 | 0.7143 | 0 | 0.0000 |
| `tournament_round_sequence` | 3 | 0.6667 | 0.7222 | 0 | 0.0000 |
| `which_first_last` | 15 | 0.0000 | 0.0190 | 0 | 0.0000 |
| `yes_no_before_after` | 44 | 0.5682 | 0.5682 | 4 | 0.0909 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 1 |
| `duration_minutes` | `number` | 14 |
| `span` | `span` | 20 |
| `span` | `yes_no` | 11 |
| `tournament_round` | `tournament_round` | 3 |
| `yes_no` | `empty` | 4 |
| `yes_no` | `yes_no` | 47 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 1 |
| `duration_minutes` | `duration_minutes` | `number` | 14 |
| `immediate_before_after` | `span` | `span` | 15 |
| `other_temporal` | `tournament_round` | `tournament_round` | 1 |
| `overlap_while_during` | `yes_no` | `yes_no` | 7 |
| `tournament_round_sequence` | `span` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `tournament_round` | 2 |
| `which_first_last` | `span` | `span` | 4 |
| `which_first_last` | `span` | `yes_no` | 11 |
| `yes_no_before_after` | `yes_no` | `empty` | 4 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 40 |

## Malformed Examples

| Question ID | Category | Gold | Predicted Answer |
| --- | --- | --- | --- |
| `tennis_000096` | `yes_no_before_after` | Yes |  |
| `tennis_000099` | `yes_no_before_after` | Yes |  |
| `tennis_000214` | `yes_no_before_after` | No |  |
| `tennis_000261` | `yes_no_before_after` | No |  |

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
