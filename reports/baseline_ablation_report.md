# Baseline and Discovery Ablation Report

Artifact root: `artifacts_discovery_ablation`
Paired rolling comparison: `artifacts_discovery_ablation\paired_rolling_error_comparison.csv`
Reference model: `constrained_structure_discovery`

This report is a methodological comparison of forecasting baselines and discovery ablations. It is not a FluSight leaderboard claim.

## Model Ranking

| series_name | model_name | test_mae | rolling_mean_mae | numerical_failure_flag |
| --- | --- | --- | --- | --- |
| Overall | delayed_observation_seir | 0.0351 | 0.0814 | False |
| Overall | deterministic_seir | 0.0351 | 0.0821 | False |
| Overall | hospitalized_seihr | 0.0361 | 0.0856 | True |
| Overall | probabilistic_seir | 0.0368 | 0.0957 | True |
| Overall | exhaustive_structure_discovery | 0.0370 | 0.0889 | False |
| Overall | no_stability_discovery | 0.0370 | 0.0889 | False |
| Overall | random_structure_discovery | 0.0370 | 0.0889 | False |
| Overall | constrained_structure_discovery | 0.0370 | 0.0889 | False |
| Overall | no_observation_search_discovery | 0.0703 | 0.0989 | False |
| Overall | validation_only_structure_selection | 0.0748 | 0.0849 | False |
| Overall | equal_weight_point_ensemble | 0.0779 | 0.0818 | False |
| Overall | fractional_seir | 0.0848 | 0.1356 | False |
| Overall | arima_auto_small | 0.1091 | 0.0435 | False |
| Overall | last_observed | 0.1091 | 0.0435 | False |
| Overall | rolling_mean_2wk | 0.1091 | 0.0588 | False |
| Overall | lagged_gradient_boosting | 0.1091 | 0.1022 | False |
| Overall | lagged_ridge | 0.1091 | 0.1022 | False |
| Overall | rolling_mean_4wk | 0.1091 | 0.1022 | False |

## Discovery Ablations

| series_name | model_name | test_mae | rolling_mean_mae | discovery_structure_name | discovery_observation_map | discovery_delay_weeks |
| --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | constrained_structure_discovery | 0.0885 | 0.1002 | SEIRS | delayed_I | 1.0000 |
| 0-4 yr | random_structure_discovery | 0.0885 | 0.1007 | SEIRS | delayed_I | 1.0000 |
| 0-4 yr | validation_only_structure_selection | 0.0885 | 0.1124 | SEIRS | delayed_I | 1.0000 |
| 0-4 yr | no_observation_search_discovery | 0.0911 | 0.1575 | SEIRS | I | 0.0000 |
| 0-4 yr | exhaustive_structure_discovery | 0.0911 | 0.1141 | SEIRS | I | 0.0000 |
| 0-4 yr | no_stability_discovery | 0.0911 | 0.1187 | SEIRS | delayed_I | 2.0000 |
| 18-49 yr | validation_only_structure_selection | 0.0152 | 0.0392 | SEIRS | I | 0.0000 |
| 18-49 yr | no_stability_discovery | 0.0480 | 0.0787 | SIR | I | 0.0000 |
| 18-49 yr | exhaustive_structure_discovery | 0.0480 | 0.0787 | SIR | I | 0.0000 |
| 18-49 yr | no_observation_search_discovery | 0.0480 | 0.0787 | SIR | I | 0.0000 |
| 18-49 yr | constrained_structure_discovery | 0.0480 | 0.0787 | SIR | I | 0.0000 |
| 18-49 yr | random_structure_discovery | 0.0486 | 0.0798 | SIR | delayed_I | 2.0000 |
| 5-17 yr | constrained_structure_discovery | 0.0044 | 0.0500 | SEIRS | delayed_I | 1.0000 |
| 5-17 yr | validation_only_structure_selection | 0.0044 | 0.0483 | SEIRS | delayed_I | 1.0000 |
| 5-17 yr | random_structure_discovery | 0.0074 | 0.0504 | SEIRS | delayed_I | 2.0000 |
| 5-17 yr | no_stability_discovery | 0.0110 | 0.0353 | SEIRS | I | 0.0000 |
| 5-17 yr | exhaustive_structure_discovery | 0.0110 | 0.0448 | SEIRS | I | 0.0000 |
| 5-17 yr | no_observation_search_discovery | 0.0534 | 0.1019 | SIR | I | 0.0000 |
| 50-64 yr | validation_only_structure_selection | 0.0321 | 0.0831 | SEIRS | I | 0.0000 |
| 50-64 yr | no_observation_search_discovery | 0.0370 | 0.0557 | SEIR | I | 0.0000 |
| 50-64 yr | exhaustive_structure_discovery | 0.0372 | 0.0540 | SIR | I | 0.0000 |
| 50-64 yr | no_stability_discovery | 0.0372 | 0.0540 | SIR | I | 0.0000 |
| 50-64 yr | random_structure_discovery | 0.0372 | 0.0540 | SIR | I | 0.0000 |
| 50-64 yr | constrained_structure_discovery | 0.0372 | 0.0540 | SIR | I | 0.0000 |
| >= 65 yr | no_observation_search_discovery | 0.1202 | 0.2321 | SIR | I | 0.0000 |
| >= 65 yr | no_stability_discovery | 0.1218 | 0.1993 | SEIRS | I | 0.0000 |
| >= 65 yr | constrained_structure_discovery | 0.1219 | 0.1748 | SEIRS | I | 0.0000 |
| >= 65 yr | exhaustive_structure_discovery | 0.1219 | 0.1690 | SEIRS | I | 0.0000 |
| >= 65 yr | validation_only_structure_selection | 0.1223 | 0.1577 | SEIRS | I | 0.0000 |
| >= 65 yr | random_structure_discovery | 0.1518 | 0.1965 | SEIRS | delayed_I | 1.0000 |
| Overall | exhaustive_structure_discovery | 0.0370 | 0.0889 | SIR | I | 0.0000 |
| Overall | no_stability_discovery | 0.0370 | 0.0889 | SIR | I | 0.0000 |
| Overall | random_structure_discovery | 0.0370 | 0.0889 | SIR | I | 0.0000 |
| Overall | constrained_structure_discovery | 0.0370 | 0.0889 | SIR | I | 0.0000 |
| Overall | no_observation_search_discovery | 0.0703 | 0.0989 | SEIRS | I | 0.0000 |
| Overall | validation_only_structure_selection | 0.0748 | 0.0849 | SEIRS | delayed_I | 2.0000 |

## Paired Rolling Comparison

| series_name | challenger_model | n_aligned | mean_abs_error_reference | mean_abs_error_challenger | mean_diff_challenger_minus_reference | ci95_low | ci95_high | reference_win_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | delayed_observation_seir | 59 | 0.1006 | 0.2213 | 0.1206 | 0.0725 | 0.1770 | 0.7627 |
| 0-4 yr | fractional_seir | 59 | 0.1006 | 0.2182 | 0.1176 | 0.0708 | 0.1604 | 0.7627 |
| 0-4 yr | deterministic_seir | 59 | 0.1006 | 0.2142 | 0.1136 | 0.0692 | 0.1628 | 0.7458 |
| 0-4 yr | hospitalized_seihr | 59 | 0.1006 | 0.2124 | 0.1118 | 0.0658 | 0.1597 | 0.7458 |
| 0-4 yr | probabilistic_seir | 59 | 0.1006 | 0.1892 | 0.0885 | 0.0469 | 0.1368 | 0.6610 |
| 0-4 yr | lagged_gradient_boosting | 59 | 0.1006 | 0.1780 | 0.0773 | 0.0271 | 0.1341 | 0.5254 |
| 0-4 yr | lagged_ridge | 59 | 0.1006 | 0.1780 | 0.0773 | 0.0281 | 0.1331 | 0.5254 |
| 0-4 yr | rolling_mean_4wk | 59 | 0.1006 | 0.1780 | 0.0773 | 0.0255 | 0.1375 | 0.5254 |
| 0-4 yr | no_observation_search_discovery | 59 | 0.1006 | 0.1571 | 0.0564 | 0.0173 | 0.1082 | 0.6949 |
| 0-4 yr | equal_weight_point_ensemble | 59 | 0.1006 | 0.1498 | 0.0491 | 0.0078 | 0.0950 | 0.5085 |
| 0-4 yr | arima_auto_small | 59 | 0.1006 | 0.1407 | 0.0400 | -0.0008 | 0.0801 | 0.5763 |
| 0-4 yr | last_observed | 59 | 0.1006 | 0.1407 | 0.0400 | 0.0021 | 0.0803 | 0.5763 |
| 0-4 yr | rolling_mean_2wk | 59 | 0.1006 | 0.1331 | 0.0324 | -0.0063 | 0.0757 | 0.4915 |
| 0-4 yr | no_stability_discovery | 59 | 0.1006 | 0.1195 | 0.0189 | 0.0059 | 0.0365 | 0.6610 |
| 0-4 yr | exhaustive_structure_discovery | 59 | 0.1006 | 0.1145 | 0.0138 | 0.0035 | 0.0234 | 0.6610 |
| 0-4 yr | validation_only_structure_selection | 59 | 0.1006 | 0.1118 | 0.0112 | -0.0000 | 0.0335 | 0.5763 |
| 0-4 yr | random_structure_discovery | 59 | 0.1006 | 0.1011 | 0.0005 | -0.0000 | 0.0015 | 0.5085 |
| 18-49 yr | fractional_seir | 59 | 0.0792 | 0.1008 | 0.0215 | 0.0113 | 0.0341 | 0.5085 |
| 18-49 yr | probabilistic_seir | 59 | 0.0792 | 0.0813 | 0.0021 | 0.0002 | 0.0043 | 0.3559 |
| 18-49 yr | random_structure_discovery | 59 | 0.0792 | 0.0803 | 0.0011 | 0.0009 | 0.0013 | 0.9492 |
| 18-49 yr | no_observation_search_discovery | 59 | 0.0792 | 0.0792 | -0.0000 | -0.0000 | 0.0000 | 0.4915 |
| 18-49 yr | exhaustive_structure_discovery | 59 | 0.0792 | 0.0792 | -0.0000 | -0.0000 | 0.0000 | 0.4068 |
| 18-49 yr | no_stability_discovery | 59 | 0.0792 | 0.0792 | -0.0000 | -0.0000 | -0.0000 | 0.3559 |
| 18-49 yr | hospitalized_seihr | 59 | 0.0792 | 0.0751 | -0.0041 | -0.0054 | -0.0027 | 0.1186 |
| 18-49 yr | deterministic_seir | 59 | 0.0792 | 0.0740 | -0.0052 | -0.0063 | -0.0041 | 0.0678 |
| 18-49 yr | delayed_observation_seir | 59 | 0.0792 | 0.0733 | -0.0059 | -0.0072 | -0.0047 | 0.0508 |
| 18-49 yr | equal_weight_point_ensemble | 59 | 0.0792 | 0.0536 | -0.0256 | -0.0320 | -0.0193 | 0.1356 |
| 18-49 yr | lagged_gradient_boosting | 59 | 0.0792 | 0.0530 | -0.0263 | -0.0357 | -0.0162 | 0.1864 |
| 18-49 yr | lagged_ridge | 59 | 0.0792 | 0.0530 | -0.0263 | -0.0357 | -0.0168 | 0.1864 |
| 18-49 yr | rolling_mean_4wk | 59 | 0.0792 | 0.0530 | -0.0263 | -0.0354 | -0.0162 | 0.1864 |
