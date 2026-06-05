# Discovery Ablation Interpretation

This report distills `artifacts_discovery_ablation` into paper-ready evidence. It does not introduce new experiments or new model code.

## 1. Why Add Forecasting Baselines And Discovery Ablations

The original benchmark compared several epidemic model families, but reviewers can reasonably ask whether the discovered structures outperform simple forecasting baselines and whether the search objective itself matters. The frozen result package answers those questions with opt-in forecasting baselines, discovery-specific ablations, and paired rolling-origin comparisons.

The relevant artifact root is `artifacts_discovery_ablation`, generated from `configs/discovery_ablation.yaml` and frozen in commit `09c9318`.

## 2. Headline Result: No Single Global Winner

The strongest paper claim is not that one discovered model dominates every setting. The evidence supports a more careful conclusion: model choice is series-dependent, and several simple or manually specified models remain competitive.

Mean performance across the six series:

| model_name | test_mae | rolling_mean_mae |
| --- | --- | --- |
| constrained_structure_discovery | 0.0561 | 0.0911 |
| validation_only_structure_selection | 0.0562 | 0.0876 |
| no_stability_discovery | 0.0577 | 0.0958 |
| exhaustive_structure_discovery | 0.0577 | 0.0916 |
| random_structure_discovery | 0.0617 | 0.0951 |
| probabilistic_seir | 0.0641 | 0.1282 |
| hospitalized_seihr | 0.0650 | 0.1248 |
| delayed_observation_seir | 0.0663 | 0.1217 |
| deterministic_seir | 0.0663 | 0.1211 |
| no_observation_search_discovery | 0.0700 | 0.1208 |

The average `test_mae` is lowest for `constrained_structure_discovery`, but the margin over `validation_only_structure_selection` is small. On `Overall`, the best test model is `delayed_observation_seir`, while `arima_auto_small` is strongest by rolling mean MAE. This argues for objective-aware reporting instead of a single global winner claim.

## 3. Pediatric 0-4 yr: Strongest Discovery Signal

The clearest discovery signal appears in the `0-4 yr` series. The recommendation table selects `constrained_structure_discovery` as `stability_preferred`, with selected structure `SEIRS` and observation map `delayed_I` at delay 1.

The compact recommendation table is available at `artifacts_discovery_ablation/paper_recommendation_table.csv`.

| series_name | recommended_model | decision_type | best_test_model | best_test_mae | best_rolling_model | best_rolling_mean_mae | recommended_discovery_structure | observation_map | delay_weeks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Overall | delayed_observation_seir | test_preferred | delayed_observation_seir | 0.0351 | arima_auto_small | 0.0435 |  |  |  |
| 0-4 yr | constrained_structure_discovery | stability_preferred | arima_auto_small | 0.0818 | constrained_structure_discovery | 0.1002 | SEIRS | delayed_I | 1.0000 |
| 5-17 yr | rolling_mean_2wk | balanced_tradeoff | arima_auto_small | 0.0000 | no_stability_discovery | 0.0353 |  |  |  |
| 18-49 yr | arima_auto_small | consensus | arima_auto_small | 0.0091 | arima_auto_small | 0.0304 |  |  |  |
| 50-64 yr | exhaustive_structure_discovery | balanced_tradeoff | validation_only_structure_selection | 0.0321 | delayed_observation_seir | 0.0528 | SIR | I | 0.0000 |
| >= 65 yr | validation_only_structure_selection | stability_preferred | fractional_seir | 0.1196 | validation_only_structure_selection | 0.1577 | SEIRS | I | 0.0000 |

For this group, disabling observation-map search worsens rolling error relative to constrained discovery, supporting the novelty of observation-aware structure search.

## 4. Observation-Map Search Matters

The direct comparison between `constrained_structure_discovery` and `no_observation_search_discovery` is summarized below. Positive deltas mean the no-observation-search ablation has higher error, so the constrained model is better.

| series_name | delta_test_mae_no_observation_minus_constrained | delta_rolling_mean_mae_no_observation_minus_constrained | constrained_observation_map | no_observation_observation_map |
| --- | --- | --- | --- | --- |
| Overall | 0.0333 | 0.0100 | I | I |
| 0-4 yr | 0.0026 | 0.0573 | delayed_I | I |
| 5-17 yr | 0.0491 | 0.0519 | delayed_I | I |
| 18-49 yr | -0.0000 | -0.0000 | I | I |
| 50-64 yr | -0.0002 | 0.0017 | I | I |
| >= 65 yr | -0.0017 | 0.0573 | I | I |

The largest observation-search benefit appears for `0-4 yr` in rolling-origin error. Other series often select `I` under both settings, which is useful negative evidence: the observation-map search is not uniformly helpful, but it can matter strongly for specific age strata.

## 5. Adult Groups: Simple Baselines And Manual Models Remain Competitive

Adult series show that simple forecasting baselines and hand-designed epidemic models remain strong competitors. For example, `18-49 yr` is best by both test and rolling metrics for `arima_auto_small` in the recommendation table. On `Overall`, `delayed_observation_seir` has the best test MAE.

This should be framed as a strength of the benchmark rather than a weakness of discovery: the pipeline identifies when discovery is useful and when simpler baselines are sufficient.

## 6. Objective-Dependent Recommendations

Several series have different test and rolling winners. The `>= 65 yr` series has `fractional_seir` as the best test model but `validation_only_structure_selection` as the best rolling model. The `50-64 yr` series has `validation_only_structure_selection` as best test model and `delayed_observation_seir` as best rolling model.

This supports the age-aware and objective-aware narrative: recommendations should report the decision criterion, not just a leaderboard rank.

## 7. Paired Rolling-Origin Evidence

The paired rolling comparison aligns forecasts by `series_name`, `horizon`, and `target_t`. Positive values of `mean_diff_challenger_minus_reference` mean `constrained_structure_discovery` has lower rolling absolute error than the challenger.

Key comparisons are available at `artifacts_discovery_ablation/paired_rolling_key_comparisons.csv`.

| series_name | challenger_model | mean_diff_challenger_minus_reference | ci95_low | ci95_high | interpretation |
| --- | --- | --- | --- | --- | --- |
| Overall | deterministic_seir | -0.0068 | -0.0089 | -0.0047 | challenger_lower_error |
| Overall | delayed_observation_seir | -0.0075 | -0.0097 | -0.0052 | challenger_lower_error |
| Overall | arima_auto_small | -0.0473 | -0.0677 | -0.0298 | challenger_lower_error |
| Overall | no_observation_search_discovery | 0.0093 | -0.0151 | 0.0308 | uncertain_ci_crosses_zero |
| Overall | validation_only_structure_selection | -0.0048 | -0.0293 | 0.0190 | uncertain_ci_crosses_zero |
| Overall | random_structure_discovery | 0.0000 | -0.0000 | 0.0000 | uncertain_ci_crosses_zero |
| 0-4 yr | deterministic_seir | 0.1136 | 0.0692 | 0.1628 | reference_lower_error |
| 0-4 yr | delayed_observation_seir | 0.1206 | 0.0725 | 0.1770 | reference_lower_error |
| 0-4 yr | arima_auto_small | 0.0400 | -0.0008 | 0.0801 | uncertain_ci_crosses_zero |
| 0-4 yr | no_observation_search_discovery | 0.0564 | 0.0173 | 0.1082 | reference_lower_error |
| 0-4 yr | validation_only_structure_selection | 0.0112 | -0.0000 | 0.0335 | uncertain_ci_crosses_zero |
| 0-4 yr | random_structure_discovery | 0.0005 | -0.0000 | 0.0015 | uncertain_ci_crosses_zero |
| 5-17 yr | deterministic_seir | 0.0293 | 0.0151 | 0.0435 | reference_lower_error |
| 5-17 yr | delayed_observation_seir | 0.0300 | 0.0158 | 0.0440 | reference_lower_error |
| 5-17 yr | arima_auto_small | -0.0136 | -0.0332 | 0.0047 | uncertain_ci_crosses_zero |
| 5-17 yr | no_observation_search_discovery | 0.0513 | 0.0379 | 0.0642 | reference_lower_error |
| 5-17 yr | validation_only_structure_selection | -0.0027 | -0.0178 | 0.0115 | uncertain_ci_crosses_zero |
| 5-17 yr | random_structure_discovery | 0.0011 | -0.0106 | 0.0109 | uncertain_ci_crosses_zero |
| 18-49 yr | deterministic_seir | -0.0052 | -0.0063 | -0.0041 | challenger_lower_error |
| 18-49 yr | delayed_observation_seir | -0.0059 | -0.0072 | -0.0047 | challenger_lower_error |
| 18-49 yr | arima_auto_small | -0.0487 | -0.0641 | -0.0323 | challenger_lower_error |
| 18-49 yr | no_observation_search_discovery | -0.0000 | -0.0000 | 0.0000 | uncertain_ci_crosses_zero |
| 18-49 yr | validation_only_structure_selection | -0.0393 | -0.0566 | -0.0210 | challenger_lower_error |
| 18-49 yr | random_structure_discovery | 0.0011 | 0.0009 | 0.0013 | reference_lower_error |
| 50-64 yr | deterministic_seir | 0.0026 | -0.0037 | 0.0123 | uncertain_ci_crosses_zero |
| 50-64 yr | delayed_observation_seir | -0.0013 | -0.0042 | 0.0017 | uncertain_ci_crosses_zero |
| 50-64 yr | arima_auto_small | 0.0063 | -0.0132 | 0.0241 | uncertain_ci_crosses_zero |
| 50-64 yr | no_observation_search_discovery | 0.0018 | -0.0012 | 0.0065 | uncertain_ci_crosses_zero |
| 50-64 yr | validation_only_structure_selection | 0.0283 | 0.0117 | 0.0448 | reference_lower_error |
| 50-64 yr | random_structure_discovery | -0.0000 | -0.0000 | 0.0000 | uncertain_ci_crosses_zero |
| >= 65 yr | deterministic_seir | 0.0467 | -0.0241 | 0.1214 | uncertain_ci_crosses_zero |
| >= 65 yr | delayed_observation_seir | 0.0467 | -0.0243 | 0.1179 | uncertain_ci_crosses_zero |
| >= 65 yr | arima_auto_small | 0.0338 | -0.0415 | 0.1103 | uncertain_ci_crosses_zero |
| >= 65 yr | no_observation_search_discovery | 0.0575 | -0.0167 | 0.1349 | uncertain_ci_crosses_zero |
| >= 65 yr | validation_only_structure_selection | -0.0185 | -0.0623 | 0.0075 | uncertain_ci_crosses_zero |
| >= 65 yr | random_structure_discovery | 0.0201 | -0.0311 | 0.0497 | uncertain_ci_crosses_zero |

These paired results are post-hoc evidence, not model-selection input. They should be used to describe robustness of rolling-origin performance, not to select models after seeing test outcomes.

## 8. Limitations

- These are retrospective FluSurv-NET-style benchmarks, not a FluSight leaderboard claim.
- Some epidemic model fits are flagged for numerical instability. Those rows are retained for transparency and should not be used to support positive claims.
- The result freeze evaluates the current grammar and budget. It does not include FluSight, Flusion, SINDy, or symbolic regression baselines.
- The observation-map search story is strongest for pediatric `0-4 yr`; other age groups provide mixed or negative evidence.

## 9. Paper-Ready Claim Language

Recommended cautious claim:

> Across six FluSurv-NET series, constrained structure discovery achieved the best mean test MAE among evaluated model families, but no model dominated all strata. Observation-aware discovery was most valuable for the pediatric 0-4 yr series, where the selected SEIRS delayed-observation structure improved rolling-origin stability relative to an observation-fixed ablation. Adult strata often favored simpler forecasting baselines or hand-specified epidemic models, motivating objective-aware and age-aware model recommendations.
