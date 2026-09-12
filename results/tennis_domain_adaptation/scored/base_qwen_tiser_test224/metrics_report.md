# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 224
- Exact Match: 0.3750
- Token F1: 0.4200
- Malformed outputs: 5 (0.0223)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 29 | 0.4138 | 0.4138 | 0 | 0.0000 |
| `immediate_before_after` | 39 | 0.0513 | 0.2467 | 0 | 0.0000 |
| `other_temporal` | 3 | 0.0000 | 0.2222 | 0 | 0.0000 |
| `overlap_while_during` | 23 | 0.7826 | 0.7826 | 0 | 0.0000 |
| `tennis_injury_or_medical` | 1 | 0.0000 | 0.0000 | 0 | 0.0000 |
| `tournament_round_sequence` | 4 | 0.5000 | 0.5417 | 0 | 0.0000 |
| `which_first_last` | 47 | 0.1277 | 0.1622 | 0 | 0.0000 |
| `yes_no_before_after` | 78 | 0.5641 | 0.5641 | 5 | 0.0641 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 4 |
| `duration_minutes` | `number` | 24 |
| `duration_minutes` | `span` | 1 |
| `span` | `number` | 2 |
| `span` | `span` | 63 |
| `span` | `yes_no` | 26 |
| `tournament_round` | `tournament_round` | 3 |
| `yes_no` | `empty` | 5 |
| `yes_no` | `yes_no` | 96 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 4 |
| `duration_minutes` | `duration_minutes` | `number` | 24 |
| `duration_minutes` | `duration_minutes` | `span` | 1 |
| `immediate_before_after` | `span` | `span` | 39 |
| `other_temporal` | `span` | `number` | 1 |
| `other_temporal` | `span` | `yes_no` | 1 |
| `other_temporal` | `tournament_round` | `tournament_round` | 1 |
| `overlap_while_during` | `span` | `span` | 1 |
| `overlap_while_during` | `yes_no` | `yes_no` | 22 |
| `tennis_injury_or_medical` | `span` | `number` | 1 |
| `tournament_round_sequence` | `span` | `span` | 1 |
| `tournament_round_sequence` | `tournament_round` | `tournament_round` | 2 |
| `tournament_round_sequence` | `yes_no` | `yes_no` | 1 |
| `which_first_last` | `span` | `span` | 22 |
| `which_first_last` | `span` | `yes_no` | 25 |
| `yes_no_before_after` | `yes_no` | `empty` | 5 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 73 |

## Malformed Examples

| Question ID | Category | Gold | Predicted Answer |
| --- | --- | --- | --- |
| `tennis_000096` | `yes_no_before_after` | Yes |  |
| `tennis_000099` | `yes_no_before_after` | Yes |  |
| `tennis_000214` | `yes_no_before_after` | No |  |
| `tennis_000261` | `yes_no_before_after` | No |  |
| `tennis_000614` | `yes_no_before_after` | Yes |  |

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
