# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 10
- Exact Match: 0.6000
- Token F1: 0.6821
- Malformed outputs: 0 (0.0000)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 1 | 0.0000 | 0.0000 | 0 | 0.0000 |
| `immediate_before_after` | 2 | 0.5000 | 0.8333 | 0 | 0.0000 |
| `overlap_while_during` | 1 | 1.0000 | 1.0000 | 0 | 0.0000 |
| `which_first_last` | 2 | 0.0000 | 0.0769 | 0 | 0.0000 |
| `yes_no_before_after` | 4 | 1.0000 | 1.0000 | 0 | 0.0000 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `number` | 1 |
| `span` | `span` | 4 |
| `yes_no` | `yes_no` | 5 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `number` | 1 |
| `immediate_before_after` | `span` | `span` | 2 |
| `overlap_while_during` | `yes_no` | `yes_no` | 1 |
| `which_first_last` | `span` | `span` | 2 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 4 |

## Malformed Examples

No malformed outputs were detected.

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
