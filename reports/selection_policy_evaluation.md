# Offline Selection Policy Evaluation

This is a deterministic offline policy evaluation over compact time-series forecasting benchmark summaries.
It does not call external LLM/API services, does not run new model experiments, and does not provide
intervention guidance or operational recommendations.

## Scope

- Frozen artifact root: `artifacts_discovery_ablation`.
- Multi-season artifact root: `artifacts_multiseason_robustness_compact`.
- Candidate records: 30.
- Verified candidates: 30.
- Series audited: 6.
- Main policy: `pareto_epsilon`.
- Ablation policy: deterministic weighted scoring.
- Hard-veto policy: decision-tree safety and simplicity rules.

## Claim-Boundary Audit

The audit labels support cautious statements such as no single global winner, group-specific signals,
simple baselines remaining competitive, and flagged rows being descriptive only. It rejects global
structured-search superiority, forecasting state-of-the-art claims, and using flagged rows as positive evidence.

| audit_label | value |
| --- | --- |
| no_single_global_winner | True |
| age_or_group_specific_signal | True |
| simple_baseline_competitive | True |
| flagged_rows_descriptive_only | True |
| posthoc_comparison_not_selection | True |
| multiseason_mixed_if_present | True |
| caveat | posthoc comparisons are not selection evidence |
| caveat | flagged rows are descriptive only |
| caveat | multi-season appendix is mixed under reduced budget |
| rejected_claim | global structured-search superiority |
| rejected_claim | forecasting state of the art |
| rejected_claim | flagged rows as positive evidence |
| rejected_claim | medical or intervention recommendation |

## Policy Recommendations

| series_name | policy_name | selected_model_name | rationale |
| --- | --- | --- | --- |
| 0-4 yr | hard_veto_decision_tree | constrained_structure_discovery | observation_label_search_preferred |
| 0-4 yr | pareto_epsilon | exhaustive_structure_discovery | selected deterministic tie-break winner from epsilon Pareto frontier |
| 0-4 yr | weighted_rubric | constrained_structure_discovery | lowest deterministic weighted normalized score |
| 18-49 yr | hard_veto_decision_tree | arima_auto_small | baseline_sufficient |
| 18-49 yr | pareto_epsilon | arima_auto_small | selected deterministic tie-break winner from epsilon Pareto frontier |
| 18-49 yr | weighted_rubric | arima_auto_small | lowest deterministic weighted normalized score |
| 5-17 yr | hard_veto_decision_tree | arima_auto_small | baseline_sufficient |
| 5-17 yr | pareto_epsilon | rolling_mean_2wk | selected deterministic tie-break winner from epsilon Pareto frontier |
| 5-17 yr | weighted_rubric | rolling_mean_2wk | lowest deterministic weighted normalized score |
| 50-64 yr | hard_veto_decision_tree | arima_auto_small | baseline_sufficient |
| 50-64 yr | pareto_epsilon | arima_auto_small | selected deterministic tie-break winner from epsilon Pareto frontier |
| 50-64 yr | weighted_rubric | arima_auto_small | lowest deterministic weighted normalized score |
| >= 65 yr | hard_veto_decision_tree | exhaustive_structure_discovery | mixed_evidence |
| >= 65 yr | pareto_epsilon | exhaustive_structure_discovery | selected deterministic tie-break winner from epsilon Pareto frontier |
| >= 65 yr | weighted_rubric | exhaustive_structure_discovery | lowest deterministic weighted normalized score |
| Overall | hard_veto_decision_tree | arima_auto_small | baseline_sufficient |
| Overall | pareto_epsilon | arima_auto_small | selected deterministic tie-break winner from epsilon Pareto frontier |
| Overall | weighted_rubric | arima_auto_small | lowest deterministic weighted normalized score |

## Stage 2: Verifier Negative-Set Rejection

Stage 2 adds a negative set of invalid or misleading candidate/evidence records. The verifier should
reject malformed records, duplicate identifiers, absolute artifact paths, posthoc test metrics used as
selection evidence, flagged rows used for positive claims, and invalid observation or delay labels.

| case_id | case_type | rejected | rejection_reasons | rejection_rate |
| --- | --- | --- | --- | --- |
| missing_required_fields | candidate | True | missing_required_candidate_field;model_name_not_allowed_for_family | 1.0000 |
| duplicate_candidate_id | candidate | True | duplicate_candidate_id | 1.0000 |
| absolute_artifact_path | candidate | True | absolute_artifact_path_in_metadata | 1.0000 |
| invalid_observation_label | candidate | True | invalid_observation_label | 1.0000 |
| invalid_delay_label | candidate | True | invalid_delay_label | 1.0000 |
| selection_evidence_contains_test_metric | evidence | True | test_metric_in_selection_evidence | 1.0000 |
| flagged_row_supports_positive_claim | evidence | True | numerical_failure_cannot_support_positive_claim | 1.0000 |

## Stage 2: Budgeted Candidate Replay

The budgeted replay uses frozen compact rows only. Test MAE is retained only as a posthoc descriptive
column and is not used for selection. Candidate availability is simulated at fixed budgets per series.

| series_name | k | policy_name | selected_model_at_k | rolling_mean_mae_at_k | candidate_count_to_top_epsilon | policy_disagreement_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | 3 | pareto_epsilon | no_observation_search_discovery | 0.1575 | 5.0000 | 0.2500 |
| 0-4 yr | 3 | weighted_score | no_observation_search_discovery | 0.1575 | 5.0000 | 0.2500 |
| 0-4 yr | 3 | hard_veto_decision_tree | no_observation_search_discovery | 0.1575 | 5.0000 | 0.2500 |
| 0-4 yr | 3 | random_order_baseline | deterministic_seir | 0.2135 | 5.0000 | 0.2500 |
| 0-4 yr | 10 | pareto_epsilon | constrained_structure_discovery | 0.1002 | 5.0000 | 0.2500 |
| 0-4 yr | 10 | weighted_score | constrained_structure_discovery | 0.1002 | 5.0000 | 0.2500 |
| 0-4 yr | 10 | hard_veto_decision_tree | constrained_structure_discovery | 0.1002 | 5.0000 | 0.2500 |
| 0-4 yr | 10 | random_order_baseline | lagged_ridge | 0.1794 | 5.0000 | 0.2500 |
| 18-49 yr | 3 | pareto_epsilon | lagged_gradient_boosting | 0.0534 | 10.0000 | 0.2500 |
| 18-49 yr | 3 | weighted_score | lagged_gradient_boosting | 0.0534 | 5.0000 | 0.2500 |
| 18-49 yr | 3 | hard_veto_decision_tree | lagged_gradient_boosting | 0.0534 | 10.0000 | 0.2500 |
| 18-49 yr | 3 | random_order_baseline | random_structure_discovery | 0.0798 | 5.0000 | 0.2500 |
| 18-49 yr | 10 | pareto_epsilon | last_observed | 0.0304 | 10.0000 | 0.2500 |
| 18-49 yr | 10 | weighted_score | last_observed | 0.0304 | 5.0000 | 0.2500 |
| 18-49 yr | 10 | hard_veto_decision_tree | last_observed | 0.0304 | 10.0000 | 0.2500 |
| 18-49 yr | 10 | random_order_baseline | validation_only_structure_selection | 0.0392 | 5.0000 | 0.2500 |
| 5-17 yr | 3 | pareto_epsilon | probabilistic_seir | 0.0429 | 3.0000 | 0.2500 |
| 5-17 yr | 3 | weighted_score | probabilistic_seir | 0.0429 | 3.0000 | 0.2500 |
| 5-17 yr | 3 | hard_veto_decision_tree | probabilistic_seir | 0.0429 | 3.0000 | 0.2500 |
| 5-17 yr | 3 | random_order_baseline | validation_only_structure_selection | 0.0483 | 3.0000 | 0.2500 |
| 5-17 yr | 10 | pareto_epsilon | rolling_mean_2wk | 0.0359 | 3.0000 | 0.5000 |
| 5-17 yr | 10 | weighted_score | rolling_mean_2wk | 0.0359 | 3.0000 | 0.5000 |
| 5-17 yr | 10 | hard_veto_decision_tree | lagged_gradient_boosting | 0.0405 | 3.0000 | 0.5000 |
| 5-17 yr | 10 | random_order_baseline | deterministic_seir | 0.0799 | 3.0000 | 0.5000 |

_Showing 24 of 48 rows._

## Stage 2: Generic Toy Observation-Label Recovery

The toy task is generic numerical time-series logic only. It checks whether direct versus lagged
or mixture observation labels can be recovered from simple synthetic signals; it is not a domain mechanism simulation.

Stage 1 toy recovery rate: 1.0.

| policy_name | observation_label_recovery_rate | delay_label_recovery_rate | mean_rolling_error |
| --- | --- | --- | --- |
| pareto_epsilon | 1.0000 | 1.0000 | 0.0227 |
| random_label_baseline | 0.3000 | 0.3000 | 0.0573 |
| weighted_score | 1.0000 | 1.0000 | 0.0227 |

## Verifier Summary

| valid | vetoed | count |
| --- | --- | --- |
| True | False | 30 |

## Caveats

- Compact CSVs do not always include validation-only metrics; when absent, policies use rolling-origin MAE and record that limitation.
- Policy outputs are model-selection interpretations over existing artifacts, not new forecasting results.
- The toy task is only a deterministic software check for observation-label logic.
