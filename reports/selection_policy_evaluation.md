# Offline Selection Policy Evaluation

This is a deterministic offline policy evaluation over compact time-series forecasting benchmark summaries.
It does not call external LLM/API services, does not run new model experiments, and does not provide
biological protocols, intervention guidance, or medical recommendations.

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

## Deterministic Toy Observation Recovery

The toy task is generic numerical time-series logic only. It checks whether direct versus lagged
observation labels can be recovered from simple synthetic signals; it is not a biological simulation.

Toy recovery rate: 1.000.

| scenario_name | seed | true_observation_label | selected_observation_label | recovered |
| --- | --- | --- | --- | --- |
| sinusoidal_direct | 1 | direct | direct | True |
| sinusoidal_direct | 2 | direct | direct | True |
| lagged_observation | 1 | lagged_2 | lagged_2 | True |
| lagged_observation | 2 | lagged_2 | lagged_2 | True |

## Verifier Summary

| valid | vetoed | count |
| --- | --- | --- |
| True | False | 30 |

## Caveats

- Compact CSVs do not always include validation-only metrics; when absent, policies use rolling-origin MAE and record that limitation.
- Policy outputs are model-selection interpretations over existing artifacts, not new forecasting results.
- The toy task is only a deterministic software check for observation-label logic.
