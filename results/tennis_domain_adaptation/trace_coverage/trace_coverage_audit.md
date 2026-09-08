# Tennis Trace-Coverage Audit

**Status:** `pass`

The 600-record artifact is the ordered output of the first 12 non-pilot batches. The cutoff is operational, not a recorded quality filter.

## Counts

| Item | Count |
| --- | ---: |
| `train` | 785 |
| `pilot` | 50 |
| `manifest_selected_after_pilot_exclusion` | 735 |
| `manifest_batches` | 15 |
| `consumed_complete_batches` | 12 |
| `reported_traced_full` | 600 |
| `ungenerated_tail` | 135 |
| `absent_from_reported_traced_full` | 185 |

## Integrity checks

- [x] `pilot_is_first_train_block`
- [x] `manifest_is_train_minus_pilot_in_order`
- [x] `manifest_batches_flatten_to_selected_ids`
- [x] `traced_is_manifest_prefix`
- [x] `pilot_and_traced_are_disjoint`
- [x] `missing_is_exactly_pilot_plus_ungenerated_tail`
- [x] `all_ids_belong_to_train`

## Interpretation

- The 50 pilot records validate separately but were not concatenated into tennis_train_traced_full.json.
- Requests exist for the final 135 selected IDs in batches 13-15, but no corresponding generated output is committed.
- This coverage audit explains selection mechanics only; semantic quality is evaluated separately.

The missing 185 records are therefore the disjoint union of the valid 50-record pilot and the 135-record ungenerated tail. No quality flag, exclusion-reason field, or alternative sampling rule is present in the tracked artifacts.
