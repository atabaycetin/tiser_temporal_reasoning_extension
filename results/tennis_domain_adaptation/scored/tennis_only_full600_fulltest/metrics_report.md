# Tennis Evaluation Metrics

## Summary

- Predictions: `predictions.jsonl`
- Total examples: 20
- Exact Match: 0.4500
- Token F1: 0.4944
- Malformed outputs: 0 (0.0000)

## Per-Category Metrics

| Category | N | EM | F1 | Malformed | Malformed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `duration_minutes` | 3 | 0.3333 | 0.3333 | 0 | 0.0000 |
| `immediate_before_after` | 3 | 0.3333 | 0.6296 | 0 | 0.0000 |
| `overlap_while_during` | 4 | 0.7500 | 0.7500 | 0 | 0.0000 |
| `which_first_last` | 4 | 0.5000 | 0.5000 | 0 | 0.0000 |
| `yes_no_before_after` | 6 | 0.3333 | 0.3333 | 0 | 0.0000 |

## Answer-Type Confusion

| Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | 3 |
| `span` | `span` | 7 |
| `yes_no` | `yes_no` | 10 |

## Category Answer-Type Confusion

| Category | Gold Answer Type | Predicted Answer Type | Count |
| --- | --- | --- | ---: |
| `duration_minutes` | `duration_minutes` | `duration_minutes` | 3 |
| `immediate_before_after` | `span` | `span` | 3 |
| `overlap_while_during` | `yes_no` | `yes_no` | 4 |
| `which_first_last` | `span` | `span` | 4 |
| `yes_no_before_after` | `yes_no` | `yes_no` | 6 |

## Malformed Examples

No malformed outputs were detected.

## Normalization

- Lowercase with Unicode NFKC normalization.
- Normalize curly apostrophes and Unicode dash variants.
- Normalize `No. 1`, `no 1`, `#1`, and `number 1` ranking answers to `1`.
- Normalize numeric `minute`/`minutes` duration answers to singular `minute`.
- Remove punctuation and English articles, then collapse whitespace.
