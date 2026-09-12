# Tennis Evaluation Metrics

## Summary

- Predictions: `/content/drive/Othercomputers/My Mac/Desktop/Folders/Documents n Stuff/Polito/DNLP/Project/tiser_temporal_reasoning_extension/results/forgetting_replay/study_v2/evaluations/selection/tennis/C0/predictions.jsonl`
- Total examples: 224
- Exact Match: 0.5804
- Token F1: 0.7012
- Malformed outputs: 0 (0.0000)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 29 | 0.6207 | 0.6207 | 0 | 0.0000 |
| `immediate_before_after` | 39 | 0.1795 | 0.5646 | 0 | 0.0000 |
| `other_temporal` | 3 | 0.3333 | 0.5111 | 0 | 0.0000 |
| `overlap_while_during` | 23 | 0.8261 | 0.8261 | 0 | 0.0000 |
| `tennis_injury_or_medical` | 1 | 0.0000 | 0.2500 | 0 | 0.0000 |
| `tournament_round_sequence` | 4 | 0.5000 | 0.5000 | 0 | 0.0000 |
| `which_first_last` | 47 | 0.3404 | 0.5800 | 0 | 0.0000 |
| `yes_no_before_after` | 78 | 0.8590 | 0.8590 | 0 | 0.0000 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 5 |
| `duration_minutes` | `number` | 20 |
| `duration_minutes` | `span` | 4 |
| `span` | `span` | 87 |
| `span` | `yes_no` | 4 |
| `tournament_round` | `span` | 1 |
| `tournament_round` | `tournament_round` | 2 |
| `yes_no` | `yes_no` | 101 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 5 |
| `duration_minutes` | `duration_minutes` | `number` | 20 |
| `duration_minutes` | `duration_minutes` | `span` | 4 |
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
| `which_first_last` | `span` | `span` | 43 |
| `which_first_last` | `span` | `yes_no` | 4 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 78 |

## Malformed Examples

No malformed outputs were detected.

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
