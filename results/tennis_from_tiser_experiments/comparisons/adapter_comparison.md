# Tennis Adapter Comparison

- Generated at: `2026-06-16T13:03:31`
- Delta baseline: not available

## Overall

| Condition | Model | Prompt | No Adapter | Adapter (recorded path) | N | EM | F1 | Malformed | Malformed Rate | Delta EM | Delta F1 |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `base_qwen_standard_fulltest` | `Qwen/Qwen2.5-0.5B-Instruct` | `standard` | true | `` | 20 | 0.4000 | 0.4494 | 0 | 0.0000 |  |  |
| `base_qwen_standard_smoke_10` | `Qwen/Qwen2.5-0.5B-Instruct` | `standard` | true | `` | 10 | 0.6000 | 0.6821 | 0 | 0.0000 |  |  |
| `base_qwen_standard_smoke_100` | `Qwen/Qwen2.5-0.5B-Instruct` | `standard` | true | `` | 100 | 0.3800 | 0.4504 | 0 | 0.0000 |  |  |
| `base_qwen_standard_test224` | `Qwen/Qwen2.5-0.5B-Instruct` | `standard` | true | `` | 224 | 0.3795 | 0.4717 | 0 | 0.0000 |  |  |
| `base_qwen_tiser_fulltest` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | true | `` | 20 | 0.5000 | 0.5785 | 0 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_10` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | true | `` | 10 | 0.6000 | 0.7417 | 0 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_100` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | true | `` | 100 | 0.3800 | 0.4014 | 4 | 0.0400 |  |  |
| `base_qwen_tiser_test224` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | true | `` | 224 | 0.3750 | 0.4200 | 5 | 0.0223 |  |  |
| `tennis_only_full600_fulltest` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | false | `model/tiser_tennis_full600_smoke/adapter` | 20 | 0.4500 | 0.4944 | 0 | 0.0000 |  |  |
| `tennis_only_full600_smoke_100` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | false | `model/tiser_tennis_full600_smoke/adapter` | 100 | 0.4700 | 0.5158 | 0 | 0.0000 |  |  |
| `tennis_only_full600_test224` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | false | `model/tiser_tennis_full600_smoke/adapter` | 224 | 0.4643 | 0.5164 | 0 | 0.0000 |  |  |
| `tennis_only_trace50_smoke_100` | `Qwen/Qwen2.5-0.5B-Instruct` | `tiser` | false | `model/tiser_tennis_smoke/adapter` | 100 | 0.3300 | 0.3767 | 1 | 0.0100 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_095331_002` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_095331_002/adapter` | 224 | 0.6473 | 0.7787 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p0_20260616_095331_001` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p0_20260616_095331_001/adapter` | 224 | 0.6473 | 0.7787 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_095331_004` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_095331_004/adapter` | 224 | 0.5670 | 0.6815 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p0_20260616_095331_003` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p0_20260616_095331_003/adapter` | 224 | 0.5670 | 0.6815 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_095331_006` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_095331_006/adapter` | 224 | 0.6920 | 0.8213 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p0_20260616_095331_005` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p0_20260616_095331_005/adapter` | 224 | 0.6741 | 0.8095 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_006` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_006/adapter` | 224 | 0.6071 | 0.7408 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p0_20260616_095331_007` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p0_20260616_095331_007/adapter` | 224 | 0.6071 | 0.7408 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_001` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e1_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_001/adapter` | 224 | 0.5670 | 0.6812 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_002` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e1_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_002/adapter` | 224 | 0.5402 | 0.6565 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_009` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e2_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_009/adapter` | 224 | 0.7098 | 0.8358 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_010` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e2_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_010/adapter` | 224 | 0.6473 | 0.7847 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011/adapter` | 224 | 0.7321 | 0.8558 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_012` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e2_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_012/adapter` | 224 | 0.6964 | 0.8276 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_007` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e2_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_007/adapter` | 224 | 0.6652 | 0.8054 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_008` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e2_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_008/adapter` | 224 | 0.5580 | 0.6792 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_015` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e3_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_015/adapter` | 224 | 0.7277 | 0.8466 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_016` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e3_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_016/adapter` | 224 | 0.7009 | 0.8361 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_018` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e3_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_018/adapter` | 224 | 0.7277 | 0.8465 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_013` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e3_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_013/adapter` | 224 | 0.7098 | 0.8381 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_014` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_e3_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_014/adapter` | 224 | 0.6205 | 0.7523 | 0 | 0.0000 |  |  |
| `tennis_from_tiser_qwen7b_20260616_093822` | `Qwen/Qwen2.5-7B-Instruct` | `tiser` | false | `model/tennis_from_tiser_qwen7b_20260616_093822/adapter` | 224 | 0.7098 | 0.8204 | 0 | 0.0000 |  |  |

## Per Category

| Condition | Category | N | EM | F1 | Malformed Rate | Delta EM | Delta F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `base_qwen_standard_fulltest` | `duration_minutes` | 3 | 0.0000 | 0.0000 | 0.0000 |  |  |
| `base_qwen_standard_fulltest` | `immediate_before_after` | 3 | 0.3333 | 0.6111 | 0.0000 |  |  |
| `base_qwen_standard_fulltest` | `overlap_while_during` | 4 | 0.5000 | 0.5000 | 0.0000 |  |  |
| `base_qwen_standard_fulltest` | `which_first_last` | 4 | 0.0000 | 0.0385 | 0.0000 |  |  |
| `base_qwen_standard_fulltest` | `yes_no_before_after` | 6 | 0.8333 | 0.8333 | 0.0000 |  |  |
| `base_qwen_standard_smoke_10` | `duration_minutes` | 1 | 0.0000 | 0.0000 | 0.0000 |  |  |
| `base_qwen_standard_smoke_10` | `immediate_before_after` | 2 | 0.5000 | 0.8333 | 0.0000 |  |  |
| `base_qwen_standard_smoke_10` | `overlap_while_during` | 1 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `base_qwen_standard_smoke_10` | `which_first_last` | 2 | 0.0000 | 0.0769 | 0.0000 |  |  |
| `base_qwen_standard_smoke_10` | `yes_no_before_after` | 4 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `base_qwen_standard_smoke_100` | `duration_minutes` | 15 | 0.2000 | 0.2000 | 0.0000 |  |  |
| `base_qwen_standard_smoke_100` | `immediate_before_after` | 15 | 0.1333 | 0.4784 | 0.0000 |  |  |
| `base_qwen_standard_smoke_100` | `other_temporal` | 1 | 0.0000 | 0.0000 | 0.0000 |  |  |
| `base_qwen_standard_smoke_100` | `overlap_while_during` | 7 | 0.5714 | 0.5714 | 0.0000 |  |  |
| `base_qwen_standard_smoke_100` | `tournament_round_sequence` | 3 | 0.6667 | 0.7222 | 0.0000 |  |  |
| `base_qwen_standard_smoke_100` | `which_first_last` | 15 | 0.0667 | 0.1798 | 0.0000 |  |  |
| `base_qwen_standard_smoke_100` | `yes_no_before_after` | 44 | 0.5909 | 0.5909 | 0.0000 |  |  |
| `base_qwen_standard_test224` | `duration_minutes` | 29 | 0.3448 | 0.3448 | 0.0000 |  |  |
| `base_qwen_standard_test224` | `immediate_before_after` | 39 | 0.1026 | 0.4420 | 0.0000 |  |  |
| `base_qwen_standard_test224` | `other_temporal` | 3 | 0.0000 | 0.4444 | 0.0000 |  |  |
| `base_qwen_standard_test224` | `overlap_while_during` | 23 | 0.6522 | 0.6947 | 0.0000 |  |  |
| `base_qwen_standard_test224` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.0000 | 0.0000 |  |  |
| `base_qwen_standard_test224` | `tournament_round_sequence` | 4 | 0.5000 | 0.5417 | 0.0000 |  |  |
| `base_qwen_standard_test224` | `which_first_last` | 47 | 0.1702 | 0.2753 | 0.0000 |  |  |
| `base_qwen_standard_test224` | `yes_no_before_after` | 78 | 0.5897 | 0.5897 | 0.0000 |  |  |
| `base_qwen_tiser_fulltest` | `duration_minutes` | 3 | 0.6667 | 0.6667 | 0.0000 |  |  |
| `base_qwen_tiser_fulltest` | `immediate_before_after` | 3 | 0.0000 | 0.5235 | 0.0000 |  |  |
| `base_qwen_tiser_fulltest` | `overlap_while_during` | 4 | 0.7500 | 0.7500 | 0.0000 |  |  |
| `base_qwen_tiser_fulltest` | `which_first_last` | 4 | 0.0000 | 0.0000 | 0.0000 |  |  |
| `base_qwen_tiser_fulltest` | `yes_no_before_after` | 6 | 0.8333 | 0.8333 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_10` | `duration_minutes` | 1 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_10` | `immediate_before_after` | 2 | 0.0000 | 0.7083 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_10` | `overlap_while_during` | 1 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_10` | `which_first_last` | 2 | 0.0000 | 0.0000 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_10` | `yes_no_before_after` | 4 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_100` | `duration_minutes` | 15 | 0.3333 | 0.3333 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_100` | `immediate_before_after` | 15 | 0.0667 | 0.1792 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_100` | `other_temporal` | 1 | 0.0000 | 0.0000 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_100` | `overlap_while_during` | 7 | 0.7143 | 0.7143 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_100` | `tournament_round_sequence` | 3 | 0.6667 | 0.7222 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_100` | `which_first_last` | 15 | 0.0000 | 0.0190 | 0.0000 |  |  |
| `base_qwen_tiser_smoke_100` | `yes_no_before_after` | 44 | 0.5682 | 0.5682 | 0.0909 |  |  |
| `base_qwen_tiser_test224` | `duration_minutes` | 29 | 0.4138 | 0.4138 | 0.0000 |  |  |
| `base_qwen_tiser_test224` | `immediate_before_after` | 39 | 0.0513 | 0.2467 | 0.0000 |  |  |
| `base_qwen_tiser_test224` | `other_temporal` | 3 | 0.0000 | 0.2222 | 0.0000 |  |  |
| `base_qwen_tiser_test224` | `overlap_while_during` | 23 | 0.7826 | 0.7826 | 0.0000 |  |  |
| `base_qwen_tiser_test224` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.0000 | 0.0000 |  |  |
| `base_qwen_tiser_test224` | `tournament_round_sequence` | 4 | 0.5000 | 0.5417 | 0.0000 |  |  |
| `base_qwen_tiser_test224` | `which_first_last` | 47 | 0.1277 | 0.1622 | 0.0000 |  |  |
| `base_qwen_tiser_test224` | `yes_no_before_after` | 78 | 0.5641 | 0.5641 | 0.0641 |  |  |
| `tennis_only_full600_fulltest` | `duration_minutes` | 3 | 0.3333 | 0.3333 | 0.0000 |  |  |
| `tennis_only_full600_fulltest` | `immediate_before_after` | 3 | 0.3333 | 0.6296 | 0.0000 |  |  |
| `tennis_only_full600_fulltest` | `overlap_while_during` | 4 | 0.7500 | 0.7500 | 0.0000 |  |  |
| `tennis_only_full600_fulltest` | `which_first_last` | 4 | 0.5000 | 0.5000 | 0.0000 |  |  |
| `tennis_only_full600_fulltest` | `yes_no_before_after` | 6 | 0.3333 | 0.3333 | 0.0000 |  |  |
| `tennis_only_full600_smoke_100` | `duration_minutes` | 15 | 0.2667 | 0.2667 | 0.0000 |  |  |
| `tennis_only_full600_smoke_100` | `immediate_before_after` | 15 | 0.3333 | 0.5514 | 0.0000 |  |  |
| `tennis_only_full600_smoke_100` | `other_temporal` | 1 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `tennis_only_full600_smoke_100` | `overlap_while_during` | 7 | 0.8571 | 0.8571 | 0.0000 |  |  |
| `tennis_only_full600_smoke_100` | `tournament_round_sequence` | 3 | 0.6667 | 0.7619 | 0.0000 |  |  |
| `tennis_only_full600_smoke_100` | `which_first_last` | 15 | 0.4000 | 0.4681 | 0.0000 |  |  |
| `tennis_only_full600_smoke_100` | `yes_no_before_after` | 44 | 0.5227 | 0.5227 | 0.0000 |  |  |
| `tennis_only_full600_test224` | `duration_minutes` | 29 | 0.3793 | 0.3793 | 0.0000 |  |  |
| `tennis_only_full600_test224` | `immediate_before_after` | 39 | 0.2308 | 0.4410 | 0.0000 |  |  |
| `tennis_only_full600_test224` | `other_temporal` | 3 | 0.6667 | 0.8889 | 0.0000 |  |  |
| `tennis_only_full600_test224` | `overlap_while_during` | 23 | 0.7391 | 0.7391 | 0.0000 |  |  |
| `tennis_only_full600_test224` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.0000 | 0.0000 |  |  |
| `tennis_only_full600_test224` | `tournament_round_sequence` | 4 | 0.7500 | 0.8214 | 0.0000 |  |  |
| `tennis_only_full600_test224` | `which_first_last` | 47 | 0.4681 | 0.5218 | 0.0000 |  |  |
| `tennis_only_full600_test224` | `yes_no_before_after` | 78 | 0.5128 | 0.5128 | 0.0000 |  |  |
| `tennis_only_trace50_smoke_100` | `duration_minutes` | 15 | 0.3333 | 0.3778 | 0.0000 |  |  |
| `tennis_only_trace50_smoke_100` | `immediate_before_after` | 15 | 0.0667 | 0.2402 | 0.0000 |  |  |
| `tennis_only_trace50_smoke_100` | `other_temporal` | 1 | 0.0000 | 0.0000 | 0.0000 |  |  |
| `tennis_only_trace50_smoke_100` | `overlap_while_during` | 7 | 0.7143 | 0.7143 | 0.0000 |  |  |
| `tennis_only_trace50_smoke_100` | `tournament_round_sequence` | 3 | 0.3333 | 0.5952 | 0.0000 |  |  |
| `tennis_only_trace50_smoke_100` | `which_first_last` | 15 | 0.0667 | 0.1076 | 0.0000 |  |  |
| `tennis_only_trace50_smoke_100` | `yes_no_before_after` | 44 | 0.4545 | 0.4545 | 0.0227 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_095331_002` | `duration_minutes` | 29 | 0.5517 | 0.5747 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_095331_002` | `immediate_before_after` | 39 | 0.2051 | 0.6852 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_095331_002` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_095331_002` | `overlap_while_during` | 23 | 0.8696 | 0.8696 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_095331_002` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_095331_002` | `tournament_round_sequence` | 4 | 0.7500 | 0.7500 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_095331_002` | `which_first_last` | 47 | 0.5532 | 0.7378 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_095331_002` | `yes_no_before_after` | 78 | 0.9103 | 0.9103 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p0_20260616_095331_001` | `duration_minutes` | 29 | 0.5517 | 0.5747 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p0_20260616_095331_001` | `immediate_before_after` | 39 | 0.2051 | 0.6852 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p0_20260616_095331_001` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p0_20260616_095331_001` | `overlap_while_during` | 23 | 0.8696 | 0.8696 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p0_20260616_095331_001` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p0_20260616_095331_001` | `tournament_round_sequence` | 4 | 0.7500 | 0.7500 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p0_20260616_095331_001` | `which_first_last` | 47 | 0.5532 | 0.7378 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga4_r16_a32_d0p0_20260616_095331_001` | `yes_no_before_after` | 78 | 0.9103 | 0.9103 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_095331_004` | `duration_minutes` | 29 | 0.5517 | 0.5747 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_095331_004` | `immediate_before_after` | 39 | 0.1282 | 0.5559 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_095331_004` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_095331_004` | `overlap_while_during` | 23 | 0.8261 | 0.8261 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_095331_004` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_095331_004` | `tournament_round_sequence` | 4 | 0.5000 | 0.5000 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_095331_004` | `which_first_last` | 47 | 0.3617 | 0.5097 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_095331_004` | `yes_no_before_after` | 78 | 0.8590 | 0.8590 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p0_20260616_095331_003` | `duration_minutes` | 29 | 0.5517 | 0.5747 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p0_20260616_095331_003` | `immediate_before_after` | 39 | 0.1282 | 0.5559 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p0_20260616_095331_003` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p0_20260616_095331_003` | `overlap_while_during` | 23 | 0.8261 | 0.8261 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p0_20260616_095331_003` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p0_20260616_095331_003` | `tournament_round_sequence` | 4 | 0.5000 | 0.5000 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p0_20260616_095331_003` | `which_first_last` | 47 | 0.3617 | 0.5097 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0001_bs4_ga8_r16_a32_d0p0_20260616_095331_003` | `yes_no_before_after` | 78 | 0.8590 | 0.8590 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_095331_006` | `duration_minutes` | 29 | 0.6897 | 0.7126 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_095331_006` | `immediate_before_after` | 39 | 0.2051 | 0.6705 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_095331_006` | `other_temporal` | 3 | 0.6667 | 0.8333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_095331_006` | `overlap_while_during` | 23 | 0.9565 | 0.9565 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_095331_006` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_095331_006` | `tournament_round_sequence` | 4 | 0.7500 | 0.8611 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_095331_006` | `which_first_last` | 47 | 0.5532 | 0.7420 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_095331_006` | `yes_no_before_after` | 78 | 0.9487 | 0.9487 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p0_20260616_095331_005` | `duration_minutes` | 29 | 0.6552 | 0.6782 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p0_20260616_095331_005` | `immediate_before_after` | 39 | 0.1795 | 0.6795 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p0_20260616_095331_005` | `other_temporal` | 3 | 0.6667 | 0.8333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p0_20260616_095331_005` | `overlap_while_during` | 23 | 0.9565 | 0.9565 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p0_20260616_095331_005` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p0_20260616_095331_005` | `tournament_round_sequence` | 4 | 0.7500 | 0.8611 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p0_20260616_095331_005` | `which_first_last` | 47 | 0.5319 | 0.7208 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga4_r16_a32_d0p0_20260616_095331_005` | `yes_no_before_after` | 78 | 0.9359 | 0.9359 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_006` | `duration_minutes` | 29 | 0.4828 | 0.5057 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_006` | `immediate_before_after` | 39 | 0.1282 | 0.6406 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_006` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_006` | `overlap_while_during` | 23 | 0.8696 | 0.8696 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_006` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_006` | `tournament_round_sequence` | 4 | 0.7500 | 0.8611 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_006` | `which_first_last` | 47 | 0.4681 | 0.6274 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_006` | `yes_no_before_after` | 78 | 0.9103 | 0.9103 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p0_20260616_095331_007` | `duration_minutes` | 29 | 0.4828 | 0.5057 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p0_20260616_095331_007` | `immediate_before_after` | 39 | 0.1282 | 0.6406 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p0_20260616_095331_007` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p0_20260616_095331_007` | `overlap_while_during` | 23 | 0.8696 | 0.8696 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p0_20260616_095331_007` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p0_20260616_095331_007` | `tournament_round_sequence` | 4 | 0.7500 | 0.8611 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p0_20260616_095331_007` | `which_first_last` | 47 | 0.4681 | 0.6274 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr0.0002_bs4_ga8_r16_a32_d0p0_20260616_095331_007` | `yes_no_before_after` | 78 | 0.9103 | 0.9103 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_001` | `duration_minutes` | 29 | 0.5172 | 0.5402 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_001` | `immediate_before_after` | 39 | 0.1282 | 0.5559 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_001` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_001` | `overlap_while_during` | 23 | 0.8261 | 0.8261 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_001` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.2500 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_001` | `tournament_round_sequence` | 4 | 0.5000 | 0.5000 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_001` | `which_first_last` | 47 | 0.3830 | 0.5310 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_001` | `yes_no_before_after` | 78 | 0.8590 | 0.8590 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_002` | `duration_minutes` | 29 | 0.5517 | 0.5517 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_002` | `immediate_before_after` | 39 | 0.1538 | 0.5485 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_002` | `other_temporal` | 3 | 0.3333 | 0.7333 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_002` | `overlap_while_during` | 23 | 0.8261 | 0.8261 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_002` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.2500 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_002` | `tournament_round_sequence` | 4 | 0.5000 | 0.5000 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_002` | `which_first_last` | 47 | 0.2766 | 0.4726 | 0.0000 |  |  |
| `tennis_from_tiser_e1_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_002` | `yes_no_before_after` | 78 | 0.8205 | 0.8205 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_009` | `duration_minutes` | 29 | 0.6897 | 0.7126 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_009` | `immediate_before_after` | 39 | 0.2308 | 0.6939 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_009` | `other_temporal` | 3 | 0.3333 | 0.5370 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_009` | `overlap_while_during` | 23 | 0.9565 | 0.9565 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_009` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_009` | `tournament_round_sequence` | 4 | 0.7500 | 0.8611 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_009` | `which_first_last` | 47 | 0.6383 | 0.8106 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_009` | `yes_no_before_after` | 78 | 0.9487 | 0.9487 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_010` | `duration_minutes` | 29 | 0.5172 | 0.5402 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_010` | `immediate_before_after` | 39 | 0.1795 | 0.6811 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_010` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_010` | `overlap_while_during` | 23 | 0.8696 | 0.8696 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_010` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_010` | `tournament_round_sequence` | 4 | 0.5000 | 0.5000 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_010` | `which_first_last` | 47 | 0.5745 | 0.7697 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_010` | `yes_no_before_after` | 78 | 0.9359 | 0.9359 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | `duration_minutes` | 29 | 0.5862 | 0.6383 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | `immediate_before_after` | 39 | 0.3077 | 0.7489 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | `other_temporal` | 3 | 0.3333 | 0.6333 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | `overlap_while_during` | 23 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | `tournament_round_sequence` | 4 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | `which_first_last` | 47 | 0.6809 | 0.8457 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga4_r16_a32_d0p05_20260616_104036_011` | `yes_no_before_after` | 78 | 0.9615 | 0.9615 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_012` | `duration_minutes` | 29 | 0.7241 | 0.7471 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_012` | `immediate_before_after` | 39 | 0.2051 | 0.6689 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_012` | `other_temporal` | 3 | 0.3333 | 0.6333 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_012` | `overlap_while_during` | 23 | 0.9565 | 0.9565 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_012` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_012` | `tournament_round_sequence` | 4 | 0.7500 | 0.8611 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_012` | `which_first_last` | 47 | 0.5745 | 0.7647 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_012` | `yes_no_before_after` | 78 | 0.9487 | 0.9487 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_007` | `duration_minutes` | 29 | 0.5862 | 0.6092 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_007` | `immediate_before_after` | 39 | 0.1795 | 0.6903 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_007` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_007` | `overlap_while_during` | 23 | 0.9130 | 0.9130 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_007` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_007` | `tournament_round_sequence` | 4 | 0.5000 | 0.5000 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_007` | `which_first_last` | 47 | 0.5957 | 0.7971 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_007` | `yes_no_before_after` | 78 | 0.9359 | 0.9359 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_008` | `duration_minutes` | 29 | 0.5172 | 0.5402 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_008` | `immediate_before_after` | 39 | 0.1282 | 0.5559 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_008` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_008` | `overlap_while_during` | 23 | 0.8261 | 0.8261 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_008` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.2500 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_008` | `tournament_round_sequence` | 4 | 0.5000 | 0.5000 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_008` | `which_first_last` | 47 | 0.3617 | 0.5428 | 0.0000 |  |  |
| `tennis_from_tiser_e2_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_008` | `yes_no_before_after` | 78 | 0.8462 | 0.8462 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_015` | `duration_minutes` | 29 | 0.6552 | 0.6782 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_015` | `immediate_before_after` | 39 | 0.3077 | 0.7350 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_015` | `other_temporal` | 3 | 0.3333 | 0.5370 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_015` | `overlap_while_during` | 23 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_015` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_015` | `tournament_round_sequence` | 4 | 0.7500 | 0.8611 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_015` | `which_first_last` | 47 | 0.6596 | 0.8280 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga4_r16_a32_d0p05_20260616_104036_015` | `yes_no_before_after` | 78 | 0.9487 | 0.9487 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_016` | `duration_minutes` | 29 | 0.6552 | 0.6782 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_016` | `immediate_before_after` | 39 | 0.2051 | 0.6894 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_016` | `other_temporal` | 3 | 0.3333 | 0.6333 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_016` | `overlap_while_during` | 23 | 0.9565 | 0.9565 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_016` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_016` | `tournament_round_sequence` | 4 | 0.7500 | 0.7500 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_016` | `which_first_last` | 47 | 0.6170 | 0.8190 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0001_bs4_ga8_r16_a32_d0p05_20260616_104036_016` | `yes_no_before_after` | 78 | 0.9615 | 0.9615 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_018` | `duration_minutes` | 29 | 0.6552 | 0.6782 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_018` | `immediate_before_after` | 39 | 0.2821 | 0.7153 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_018` | `other_temporal` | 3 | 0.3333 | 0.6333 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_018` | `overlap_while_during` | 23 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_018` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_018` | `tournament_round_sequence` | 4 | 0.7500 | 0.7500 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_018` | `which_first_last` | 47 | 0.6809 | 0.8475 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr0.0002_bs4_ga8_r16_a32_d0p05_20260616_104036_018` | `yes_no_before_after` | 78 | 0.9487 | 0.9487 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_013` | `duration_minutes` | 29 | 0.6552 | 0.6782 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_013` | `immediate_before_after` | 39 | 0.2051 | 0.6783 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_013` | `other_temporal` | 3 | 0.3333 | 0.5370 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_013` | `overlap_while_during` | 23 | 0.9565 | 0.9565 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_013` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_013` | `tournament_round_sequence` | 4 | 0.7500 | 0.7500 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_013` | `which_first_last` | 47 | 0.6596 | 0.8441 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga4_r16_a32_d0p05_20260616_104036_013` | `yes_no_before_after` | 78 | 0.9615 | 0.9615 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_014` | `duration_minutes` | 29 | 0.5517 | 0.5747 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_014` | `immediate_before_after` | 39 | 0.1538 | 0.6377 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_014` | `other_temporal` | 3 | 0.3333 | 0.6778 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_014` | `overlap_while_during` | 23 | 0.8696 | 0.8696 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_014` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_014` | `tournament_round_sequence` | 4 | 0.5000 | 0.5000 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_014` | `which_first_last` | 47 | 0.5106 | 0.6937 | 0.0000 |  |  |
| `tennis_from_tiser_e3_lr5e-05_bs4_ga8_r16_a32_d0p05_20260616_104036_014` | `yes_no_before_after` | 78 | 0.8974 | 0.8974 | 0.0000 |  |  |
| `tennis_from_tiser_qwen7b_20260616_093822` | `duration_minutes` | 29 | 0.4483 | 0.5006 | 0.0000 |  |  |
| `tennis_from_tiser_qwen7b_20260616_093822` | `immediate_before_after` | 39 | 0.3333 | 0.7360 | 0.0000 |  |  |
| `tennis_from_tiser_qwen7b_20260616_093822` | `other_temporal` | 3 | 0.0000 | 0.3606 | 0.0000 |  |  |
| `tennis_from_tiser_qwen7b_20260616_093822` | `overlap_while_during` | 23 | 1.0000 | 1.0000 | 0.0000 |  |  |
| `tennis_from_tiser_qwen7b_20260616_093822` | `tennis_injury_or_medical` | 1 | 0.0000 | 0.3333 | 0.0000 |  |  |
| `tennis_from_tiser_qwen7b_20260616_093822` | `tournament_round_sequence` | 4 | 0.7500 | 0.7500 | 0.0000 |  |  |
| `tennis_from_tiser_qwen7b_20260616_093822` | `which_first_last` | 47 | 0.7021 | 0.8325 | 0.0000 |  |  |
| `tennis_from_tiser_qwen7b_20260616_093822` | `yes_no_before_after` | 78 | 0.9487 | 0.9487 | 0.0000 |  |  |
