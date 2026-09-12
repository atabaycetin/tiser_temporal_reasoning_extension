# Tennis Adapter Comparison

- Generated at: `2026-06-07T17:16:46`
- Delta baseline: `base_qwen_standard_test224`

## Overall

| Condition | Model | Prompt | No Adapter | Adapter (recorded path) | N | EM | F1 | Malformed | Malformed Rate | Delta EM | Delta F1 |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `base_qwen_standard_fulltest` | `Qwen/Qwen2.5-0.5B-Instruct` | `standard` | true | `` | 20 | 0.4000 | 0.4494 | 0 | 0.0000 | +0.0205 | -0.0223 |
| `base_qwen_standard_smoke_10` | `Qwen/Qwen2.5-0.5B-Instruct` | `standard` | true | `` | 10 | 0.6000 | 0.6821 | 0 | 0.0000 | +0.2205 | +0.2104 |
| `base_qwen_standard_smoke_100` | `Qwen/Qwen2.5-0.5B-Instruct` | `standard` | true | `` | 100 | 0.3800 | 0.4504 | 0 | 0.0000 | +0.0005 | -0.0213 |
| `base_qwen_standard_test224` | `Qwen/Qwen2.5-0.5B-Instruct` | `standard` | true | `` | 224 | 0.3795 | 0.4717 | 0 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_tiser_fulltest` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | true | `` | 20 | 0.5000 | 0.5785 | 0 | 0.0000 | +0.1205 | +0.1069 |
| `base_qwen_tiser_smoke_10` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | true | `` | 10 | 0.6000 | 0.7417 | 0 | 0.0000 | +0.2205 | +0.2700 |
| `base_qwen_tiser_smoke_100` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | true | `` | 100 | 0.3800 | 0.4014 | 4 | 0.0400 | +0.0005 | -0.0703 |
| `base_qwen_tiser_test224` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | true | `` | 224 | 0.3750 | 0.4200 | 5 | 0.0223 | -0.0045 | -0.0517 |
| `tennis_only_full600_fulltest` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | false | `model/tiser_tennis_full600_smoke/adapter` | 20 | 0.4500 | 0.4944 | 0 | 0.0000 | +0.0705 | +0.0228 |
| `tennis_only_full600_smoke_100` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | false | `model/tiser_tennis_full600_smoke/adapter` | 100 | 0.4700 | 0.5158 | 0 | 0.0000 | +0.0905 | +0.0441 |
| `tennis_only_full600_test224` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | false | `model/tiser_tennis_full600_smoke/adapter` | 224 | 0.4643 | 0.5164 | 0 | 0.0000 | +0.0848 | +0.0447 |
| `tennis_only_trace50_smoke_100` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | false | `model/tiser_tennis_smoke/adapter` | 100 | 0.3300 | 0.3767 | 1 | 0.0100 | -0.0495 | -0.0950 |

## Per Category

| Condition | Category | N | EM | F1 | Malformed Rate | Delta EM | Delta F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `base_qwen_standard_fulltest` | `duration_minutes` | 3 | 0.0000 | 0.0000 | 0.0000 | -0.3448 | -0.3448 |
| `base_qwen_standard_fulltest` | `immediate_before_after` | 3 | 0.3333 | 0.6111 | 0.0000 | +0.2308 | +0.1691 |
| `base_qwen_standard_fulltest` | `overlap_while_during` | 4 | 0.5000 | 0.5000 | 0.0000 | -0.1522 | -0.1947 |
| `base_qwen_standard_fulltest` | `which_first_last` | 4 | 0.0000 | 0.0385 | 0.0000 | -0.1702 | -0.2368 |
| `base_qwen_standard_fulltest` | `yes_no_before_after` | 6 | 0.8333 | 0.8333 | 0.0000 | +0.2436 | +0.2436 |
| `base_qwen_standard_smoke_10` | `duration_minutes` | 1 | 0.0000 | 0.0000 | 0.0000 | -0.3448 | -0.3448 |
| `base_qwen_standard_smoke_10` | `immediate_before_after` | 2 | 0.5000 | 0.8333 | 0.0000 | +0.3974 | +0.3914 |
| `base_qwen_standard_smoke_10` | `overlap_while_during` | 1 | 1.0000 | 1.0000 | 0.0000 | +0.3478 | +0.3053 |
| `base_qwen_standard_smoke_10` | `which_first_last` | 2 | 0.0000 | 0.0769 | 0.0000 | -0.1702 | -0.1984 |
| `base_qwen_standard_smoke_10` | `yes_no_before_after` | 4 | 1.0000 | 1.0000 | 0.0000 | +0.4103 | +0.4103 |
| `base_qwen_standard_smoke_100` | `duration_minutes` | 15 | 0.2000 | 0.2000 | 0.0000 | -0.1448 | -0.1448 |
| `base_qwen_standard_smoke_100` | `immediate_before_after` | 15 | 0.1333 | 0.4784 | 0.0000 | +0.0308 | +0.0365 |
| `base_qwen_standard_smoke_100` | `other_temporal` | 1 | 0.0000 | 0.0000 | 0.0000 | +0.0000 | -0.4444 |
| `base_qwen_standard_smoke_100` | `overlap_while_during` | 7 | 0.5714 | 0.5714 | 0.0000 | -0.0807 | -0.1232 |
| `base_qwen_standard_smoke_100` | `tournament_round_sequence` | 3 | 0.6667 | 0.7222 | 0.0000 | +0.1667 | +0.1806 |
| `base_qwen_standard_smoke_100` | `which_first_last` | 15 | 0.0667 | 0.1798 | 0.0000 | -0.1035 | -0.0955 |
| `base_qwen_standard_smoke_100` | `yes_no_before_after` | 44 | 0.5909 | 0.5909 | 0.0000 | +0.0012 | +0.0012 |
| `base_qwen_standard_test224` | `duration_minutes` | 29 | 0.3448 | 0.3448 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_standard_test224` | `immediate_before_after` | 39 | 0.1026 | 0.4420 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_standard_test224` | `other_temporal` | 3 | 0.0000 | 0.4444 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_standard_test224` | `overlap_while_during` | 23 | 0.6522 | 0.6947 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_standard_test224` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.0000 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_standard_test224` | `tournament_round_sequence` | 4 | 0.5000 | 0.5417 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_standard_test224` | `which_first_last` | 47 | 0.1702 | 0.2753 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_standard_test224` | `yes_no_before_after` | 78 | 0.5897 | 0.5897 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_tiser_fulltest` | `duration_minutes` | 3 | 0.6667 | 0.6667 | 0.0000 | +0.3218 | +0.3218 |
| `base_qwen_tiser_fulltest` | `immediate_before_after` | 3 | 0.0000 | 0.5235 | 0.0000 | -0.1026 | +0.0815 |
| `base_qwen_tiser_fulltest` | `overlap_while_during` | 4 | 0.7500 | 0.7500 | 0.0000 | +0.0978 | +0.0553 |
| `base_qwen_tiser_fulltest` | `which_first_last` | 4 | 0.0000 | 0.0000 | 0.0000 | -0.1702 | -0.2753 |
| `base_qwen_tiser_fulltest` | `yes_no_before_after` | 6 | 0.8333 | 0.8333 | 0.0000 | +0.2436 | +0.2436 |
| `base_qwen_tiser_smoke_10` | `duration_minutes` | 1 | 1.0000 | 1.0000 | 0.0000 | +0.6552 | +0.6552 |
| `base_qwen_tiser_smoke_10` | `immediate_before_after` | 2 | 0.0000 | 0.7083 | 0.0000 | -0.1026 | +0.2664 |
| `base_qwen_tiser_smoke_10` | `overlap_while_during` | 1 | 1.0000 | 1.0000 | 0.0000 | +0.3478 | +0.3053 |
| `base_qwen_tiser_smoke_10` | `which_first_last` | 2 | 0.0000 | 0.0000 | 0.0000 | -0.1702 | -0.2753 |
| `base_qwen_tiser_smoke_10` | `yes_no_before_after` | 4 | 1.0000 | 1.0000 | 0.0000 | +0.4103 | +0.4103 |
| `base_qwen_tiser_smoke_100` | `duration_minutes` | 15 | 0.3333 | 0.3333 | 0.0000 | -0.0115 | -0.0115 |
| `base_qwen_tiser_smoke_100` | `immediate_before_after` | 15 | 0.0667 | 0.1792 | 0.0000 | -0.0359 | -0.2628 |
| `base_qwen_tiser_smoke_100` | `other_temporal` | 1 | 0.0000 | 0.0000 | 0.0000 | +0.0000 | -0.4444 |
| `base_qwen_tiser_smoke_100` | `overlap_while_during` | 7 | 0.7143 | 0.7143 | 0.0000 | +0.0621 | +0.0196 |
| `base_qwen_tiser_smoke_100` | `tournament_round_sequence` | 3 | 0.6667 | 0.7222 | 0.0000 | +0.1667 | +0.1806 |
| `base_qwen_tiser_smoke_100` | `which_first_last` | 15 | 0.0000 | 0.0190 | 0.0000 | -0.1702 | -0.2562 |
| `base_qwen_tiser_smoke_100` | `yes_no_before_after` | 44 | 0.5682 | 0.5682 | 0.0909 | -0.0216 | -0.0216 |
| `base_qwen_tiser_test224` | `duration_minutes` | 29 | 0.4138 | 0.4138 | 0.0000 | +0.0690 | +0.0690 |
| `base_qwen_tiser_test224` | `immediate_before_after` | 39 | 0.0513 | 0.2467 | 0.0000 | -0.0513 | -0.1953 |
| `base_qwen_tiser_test224` | `other_temporal` | 3 | 0.0000 | 0.2222 | 0.0000 | +0.0000 | -0.2222 |
| `base_qwen_tiser_test224` | `overlap_while_during` | 23 | 0.7826 | 0.7826 | 0.0000 | +0.1304 | +0.0879 |
| `base_qwen_tiser_test224` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.0000 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_tiser_test224` | `tournament_round_sequence` | 4 | 0.5000 | 0.5417 | 0.0000 | +0.0000 | +0.0000 |
| `base_qwen_tiser_test224` | `which_first_last` | 47 | 0.1277 | 0.1622 | 0.0000 | -0.0426 | -0.1131 |
| `base_qwen_tiser_test224` | `yes_no_before_after` | 78 | 0.5641 | 0.5641 | 0.0641 | -0.0256 | -0.0256 |
| `tennis_only_full600_fulltest` | `duration_minutes` | 3 | 0.3333 | 0.3333 | 0.0000 | -0.0115 | -0.0115 |
| `tennis_only_full600_fulltest` | `immediate_before_after` | 3 | 0.3333 | 0.6296 | 0.0000 | +0.2308 | +0.1877 |
| `tennis_only_full600_fulltest` | `overlap_while_during` | 4 | 0.7500 | 0.7500 | 0.0000 | +0.0978 | +0.0553 |
| `tennis_only_full600_fulltest` | `which_first_last` | 4 | 0.5000 | 0.5000 | 0.0000 | +0.3298 | +0.2247 |
| `tennis_only_full600_fulltest` | `yes_no_before_after` | 6 | 0.3333 | 0.3333 | 0.0000 | -0.2564 | -0.2564 |
| `tennis_only_full600_smoke_100` | `duration_minutes` | 15 | 0.2667 | 0.2667 | 0.0000 | -0.0782 | -0.0782 |
| `tennis_only_full600_smoke_100` | `immediate_before_after` | 15 | 0.3333 | 0.5514 | 0.0000 | +0.2308 | +0.1094 |
| `tennis_only_full600_smoke_100` | `other_temporal` | 1 | 1.0000 | 1.0000 | 0.0000 | +1.0000 | +0.5556 |
| `tennis_only_full600_smoke_100` | `overlap_while_during` | 7 | 0.8571 | 0.8571 | 0.0000 | +0.2050 | +0.1625 |
| `tennis_only_full600_smoke_100` | `tournament_round_sequence` | 3 | 0.6667 | 0.7619 | 0.0000 | +0.1667 | +0.2202 |
| `tennis_only_full600_smoke_100` | `which_first_last` | 15 | 0.4000 | 0.4681 | 0.0000 | +0.2298 | +0.1929 |
| `tennis_only_full600_smoke_100` | `yes_no_before_after` | 44 | 0.5227 | 0.5227 | 0.0000 | -0.0670 | -0.0670 |
| `tennis_only_full600_test224` | `duration_minutes` | 29 | 0.3793 | 0.3793 | 0.0000 | +0.0345 | +0.0345 |
| `tennis_only_full600_test224` | `immediate_before_after` | 39 | 0.2308 | 0.4410 | 0.0000 | +0.1282 | -0.0009 |
| `tennis_only_full600_test224` | `other_temporal` | 3 | 0.6667 | 0.8889 | 0.0000 | +0.6667 | +0.4444 |
| `tennis_only_full600_test224` | `overlap_while_during` | 23 | 0.7391 | 0.7391 | 0.0000 | +0.0870 | +0.0445 |
| `tennis_only_full600_test224` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.0000 | 0.0000 | +0.0000 | +0.0000 |
| `tennis_only_full600_test224` | `tournament_round_sequence` | 4 | 0.7500 | 0.8214 | 0.0000 | +0.2500 | +0.2798 |
| `tennis_only_full600_test224` | `which_first_last` | 47 | 0.4681 | 0.5218 | 0.0000 | +0.2979 | +0.2465 |
| `tennis_only_full600_test224` | `yes_no_before_after` | 78 | 0.5128 | 0.5128 | 0.0000 | -0.0769 | -0.0769 |
| `tennis_only_trace50_smoke_100` | `duration_minutes` | 15 | 0.3333 | 0.3778 | 0.0000 | -0.0115 | +0.0330 |
| `tennis_only_trace50_smoke_100` | `immediate_before_after` | 15 | 0.0667 | 0.2402 | 0.0000 | -0.0359 | -0.2017 |
| `tennis_only_trace50_smoke_100` | `other_temporal` | 1 | 0.0000 | 0.0000 | 0.0000 | +0.0000 | -0.4444 |
| `tennis_only_trace50_smoke_100` | `overlap_while_during` | 7 | 0.7143 | 0.7143 | 0.0000 | +0.0621 | +0.0196 |
| `tennis_only_trace50_smoke_100` | `tournament_round_sequence` | 3 | 0.3333 | 0.5952 | 0.0000 | -0.1667 | +0.0536 |
| `tennis_only_trace50_smoke_100` | `which_first_last` | 15 | 0.0667 | 0.1076 | 0.0000 | -0.1035 | -0.1677 |
| `tennis_only_trace50_smoke_100` | `yes_no_before_after` | 44 | 0.4545 | 0.4545 | 0.0227 | -0.1352 | -0.1352 |
