# Verifier-Gated Iterative Agent Loop Evaluation

This Stage 8 report evaluates a constrained multi-round structured proposer loop.
It uses verifier feedback and non-final replay evidence between rounds. It supports
proposal/refinement and candidate-budget-efficiency claims only, not forecasting SOTA,
autonomous-science, real-world mechanism-recovery, or operational forecasting claims.

## Scope

- Series: ['0-4 yr', '18-49 yr'].
- Rounds: 3.
- Candidates per round: 3.
- Budgets: [3, 6, 9].
- Replay only: True.
- External API used: False.
- API statuses: [].
- Prompt/feedback/selection audit passed: True.
- Claim audit passed: True.
- Test metric usage: posthoc_descriptive_only.

## Final Summary

| series_name | proposer_type | rounds | candidates_per_round | total_budget | final_selected_model | final_best_rolling_score | round1_to_final_improvement | final_top_epsilon_hit | budget_to_top_epsilon | mean_valid_proposal_rate | mean_duplicate_rate | family_diversity | observation_label_diversity | external_api_used | api_statuses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | mock_api_iterative | 3 | 3 | 9 | constrained_structure_discovery | 0.1002 | 0.0000 | True | 3 | 1.0000 | 0.0000 | 4 | 3 | False |  |
| 0-4 yr | mock_api_single_shot | 3 | 3 | 9 | constrained_structure_discovery | 0.1002 | 0.0000 | True | 3 |  |  | 4 | 3 | False |  |
| 0-4 yr | failure_guided_proposer | 3 | 3 | 9 | constrained_structure_discovery | 0.1002 | 0.0000 | True | 3 | 1.0000 | 0.0000 | 4 | 3 | False |  |
| 0-4 yr | random_candidate_proposer | 3 | 3 | 9 | constrained_structure_discovery | 0.1002 | 0.0000 | True | 3 | 1.0000 | 0.0000 | 4 | 3 | False |  |
| 0-4 yr | deterministic_seed_proposer | 3 | 3 | 9 | constrained_structure_discovery | 0.1002 | 0.0415 | True | 6 | 1.0000 | 0.0000 | 4 | 3 | False |  |
| 0-4 yr | oracle_reference | 3 | 3 | 9 | constrained_structure_discovery | 0.1002 | 0.0000 | True | 3 | 1.0000 | 0.0000 | 4 | 3 | False |  |
| 18-49 yr | mock_api_iterative | 3 | 3 | 9 | arima_auto_small | 0.0304 | 0.0000 | True | 3 | 1.0000 | 0.0000 | 4 | 3 | False |  |
| 18-49 yr | mock_api_single_shot | 3 | 3 | 9 | arima_auto_small | 0.0304 | 0.0000 | True | 3 |  |  | 4 | 3 | False |  |
| 18-49 yr | failure_guided_proposer | 3 | 3 | 9 | arima_auto_small | 0.0304 | 0.0000 | True | 3 | 1.0000 | 0.0000 | 4 | 3 | False |  |
| 18-49 yr | random_candidate_proposer | 3 | 3 | 9 | arima_auto_small | 0.0304 | 0.0483 | True | 6 | 1.0000 | 0.0000 | 4 | 3 | False |  |
| 18-49 yr | deterministic_seed_proposer | 3 | 3 | 9 | arima_auto_small | 0.0304 | 0.0000 | True | 3 | 1.0000 | 0.0000 | 4 | 3 | False |  |
| 18-49 yr | oracle_reference | 3 | 3 | 9 | arima_auto_small | 0.0304 | 0.0000 | True | 3 | 1.0000 | 0.0000 | 4 | 3 | False |  |

## Round Progress

| series_name | proposer_type | round_idx | proposed_count | accepted_count | valid_proposal_rate | duplicate_rate | new_useful_candidate_rate | out_of_allowlist_rejection_rate | claim_safety_violation_rate | family_diversity | observation_label_diversity | top_epsilon_hit_by_round | best_rolling_score_by_round | selected_model_by_round | candidate_jaccard_vs_previous_round |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | mock_api_iterative | 1 | 3 | 3 | 1.0000 | 0.0000 | 0.3333 | 0.0000 | 0.0000 | 3 | 3 | True | 0.1002 | constrained_structure_discovery | 1.0000 |
| 0-4 yr | mock_api_iterative | 2 | 3 | 3 | 1.0000 | 0.0000 | 0.3333 | 0.0000 | 0.0000 | 3 | 3 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 0-4 yr | mock_api_iterative | 3 | 3 | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 0-4 yr | mock_api_single_shot | 1 | 9 | 9 | 1.0000 | 0.0000 | 0.2222 | 0.0000 | 0.0000 | 4 | 3 | True | 0.1002 | constrained_structure_discovery | 1.0000 |
| 0-4 yr | mock_api_single_shot | 2 | 0 | 0 |  |  |  |  | 0.0000 | 4 | 3 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 0-4 yr | mock_api_single_shot | 3 | 0 | 0 |  |  |  |  | 0.0000 | 4 | 3 | True | 0.1002 | constrained_structure_discovery | 1.0000 |
| 0-4 yr | failure_guided_proposer | 1 | 3 | 3 | 1.0000 | 0.0000 | 0.6667 | 0.0000 | 0.0000 | 2 | 2 | True | 0.1002 | constrained_structure_discovery | 1.0000 |
| 0-4 yr | failure_guided_proposer | 2 | 3 | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 3 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 0-4 yr | failure_guided_proposer | 3 | 3 | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 0-4 yr | random_candidate_proposer | 1 | 3 | 3 | 1.0000 | 0.0000 | 0.3333 | 0.0000 | 0.0000 | 3 | 2 | True | 0.1002 | constrained_structure_discovery | 1.0000 |
| 0-4 yr | random_candidate_proposer | 2 | 3 | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 0-4 yr | random_candidate_proposer | 3 | 3 | 3 | 1.0000 | 0.0000 | 0.3333 | 0.0000 | 0.0000 | 4 | 3 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 0-4 yr | deterministic_seed_proposer | 1 | 3 | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1 | 1 | False | 0.1417 | arima_auto_small | 1.0000 |
| 0-4 yr | deterministic_seed_proposer | 2 | 3 | 3 | 1.0000 | 0.0000 | 0.3333 | 0.0000 | 0.0000 | 3 | 2 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 0-4 yr | deterministic_seed_proposer | 3 | 3 | 3 | 1.0000 | 0.0000 | 0.3333 | 0.0000 | 0.0000 | 4 | 3 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 0-4 yr | oracle_reference | 1 | 3 | 3 | 1.0000 | 0.0000 | 0.6667 | 0.0000 | 0.0000 | 2 | 1 | True | 0.1002 | constrained_structure_discovery | 1.0000 |
| 0-4 yr | oracle_reference | 2 | 3 | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 3 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 0-4 yr | oracle_reference | 3 | 3 | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 | True | 0.1002 | constrained_structure_discovery | 0.0000 |
| 18-49 yr | mock_api_iterative | 1 | 3 | 3 | 1.0000 | 0.0000 | 0.6667 | 0.0000 | 0.0000 | 1 | 1 | True | 0.0304 | arima_auto_small | 1.0000 |
| 18-49 yr | mock_api_iterative | 2 | 3 | 3 | 1.0000 | 0.0000 | 0.3333 | 0.0000 | 0.0000 | 4 | 2 | True | 0.0304 | arima_auto_small | 0.0000 |
| 18-49 yr | mock_api_iterative | 3 | 3 | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 | True | 0.0304 | arima_auto_small | 0.0000 |
| 18-49 yr | mock_api_single_shot | 1 | 9 | 9 | 1.0000 | 0.0000 | 0.2222 | 0.0000 | 0.0000 | 4 | 3 | True | 0.0304 | arima_auto_small | 1.0000 |
| 18-49 yr | mock_api_single_shot | 2 | 0 | 0 |  |  |  |  | 0.0000 | 4 | 3 | True | 0.0304 | arima_auto_small | 0.0000 |
| 18-49 yr | mock_api_single_shot | 3 | 0 | 0 |  |  |  |  | 0.0000 | 4 | 3 | True | 0.0304 | arima_auto_small | 1.0000 |
| 18-49 yr | failure_guided_proposer | 1 | 3 | 3 | 1.0000 | 0.0000 | 0.6667 | 0.0000 | 0.0000 | 1 | 1 | True | 0.0304 | arima_auto_small | 1.0000 |
| 18-49 yr | failure_guided_proposer | 2 | 3 | 3 | 1.0000 | 0.0000 | 0.3333 | 0.0000 | 0.0000 | 3 | 2 | True | 0.0304 | arima_auto_small | 0.0000 |
| 18-49 yr | failure_guided_proposer | 3 | 3 | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 | True | 0.0304 | arima_auto_small | 0.0000 |
| 18-49 yr | random_candidate_proposer | 1 | 3 | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 2 | 3 | False | 0.0787 | exhaustive_structure_discovery | 1.0000 |

_Showing 28 of 36 rows._

## Replay By Budget

| series_name | proposer_type | budget | selected_model_at_k | best_rolling_score_after_k | post_selection_test_mae | top_epsilon_hit | budget_to_top_epsilon | selection_metric_source | test_metric_usage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | mock_api_iterative | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | mock_api_iterative | 6 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | mock_api_iterative | 9 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | mock_api_single_shot | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | mock_api_single_shot | 6 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | mock_api_single_shot | 9 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | failure_guided_proposer | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | failure_guided_proposer | 6 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | failure_guided_proposer | 9 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 6 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 9 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 3 | arima_auto_small | 0.1417 | 0.0818 | False | 6 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 6 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 6 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 9 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 6 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | oracle_reference | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | oracle_reference | 6 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 0-4 yr | oracle_reference | 9 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 18-49 yr | mock_api_iterative | 3 | arima_auto_small | 0.0304 | 0.0091 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 18-49 yr | mock_api_iterative | 6 | arima_auto_small | 0.0304 | 0.0091 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 18-49 yr | mock_api_iterative | 9 | arima_auto_small | 0.0304 | 0.0091 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 18-49 yr | mock_api_single_shot | 3 | arima_auto_small | 0.0304 | 0.0091 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 18-49 yr | mock_api_single_shot | 6 | arima_auto_small | 0.0304 | 0.0091 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 18-49 yr | mock_api_single_shot | 9 | arima_auto_small | 0.0304 | 0.0091 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 18-49 yr | failure_guided_proposer | 3 | arima_auto_small | 0.0304 | 0.0091 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 18-49 yr | failure_guided_proposer | 6 | arima_auto_small | 0.0304 | 0.0091 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 18-49 yr | failure_guided_proposer | 9 | arima_auto_small | 0.0304 | 0.0091 | True | 3 | rolling_mean_mae | posthoc_descriptive_only |
| 18-49 yr | random_candidate_proposer | 3 | exhaustive_structure_discovery | 0.0787 | 0.0480 | False | 6 | rolling_mean_mae | posthoc_descriptive_only |

_Showing 28 of 36 rows._

## No-Leakage Audit

| series_name | proposer_type | round_idx | prompt_contains_test_metric | prompt_contains_test_winner | prompt_contains_test_rank | prompt_contains_posthoc_metric | feedback_contains_test_metric | selection_uses_test_metric | posthoc_test_metric_only | safe_prompt_passed | safe_feedback_passed | safe_selection_passed | allowlist_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | mock_api_iterative | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | mock_api_iterative | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | mock_api_iterative | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | mock_api_single_shot | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | mock_api_single_shot | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | mock_api_single_shot | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | failure_guided_proposer | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | failure_guided_proposer | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | failure_guided_proposer | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | random_candidate_proposer | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | random_candidate_proposer | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | random_candidate_proposer | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | deterministic_seed_proposer | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | deterministic_seed_proposer | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | deterministic_seed_proposer | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | oracle_reference | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | oracle_reference | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 0-4 yr | oracle_reference | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | mock_api_iterative | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | mock_api_iterative | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | mock_api_iterative | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | mock_api_single_shot | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | mock_api_single_shot | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | mock_api_single_shot | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | failure_guided_proposer | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | failure_guided_proposer | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | failure_guided_proposer | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | random_candidate_proposer | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | random_candidate_proposer | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | random_candidate_proposer | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | deterministic_seed_proposer | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | deterministic_seed_proposer | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | deterministic_seed_proposer | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | oracle_reference | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | oracle_reference | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| 18-49 yr | oracle_reference | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |

## Claim Audit

| series_name | proposer_type | proposal_quality_only | budget_efficiency_only | not_forecasting_performance_claim | not_sota_claim | not_autonomous_science_claim | not_mechanism_recovery_claim | claim_audit_passed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | mock_api_iterative | True | True | True | True | True | True | True |
| 0-4 yr | mock_api_single_shot | True | True | True | True | True | True | True |
| 0-4 yr | failure_guided_proposer | True | True | True | True | True | True | True |
| 0-4 yr | random_candidate_proposer | True | True | True | True | True | True | True |
| 0-4 yr | deterministic_seed_proposer | True | True | True | True | True | True | True |
| 0-4 yr | oracle_reference | True | True | True | True | True | True | True |
| 18-49 yr | mock_api_iterative | True | True | True | True | True | True | True |
| 18-49 yr | mock_api_single_shot | True | True | True | True | True | True | True |
| 18-49 yr | failure_guided_proposer | True | True | True | True | True | True | True |
| 18-49 yr | random_candidate_proposer | True | True | True | True | True | True | True |
| 18-49 yr | deterministic_seed_proposer | True | True | True | True | True | True | True |
| 18-49 yr | oracle_reference | True | True | True | True | True | True | True |

## Figures

- `paper_draft\figures\fig_iterative_agent_round_progress.pdf`
- `paper_draft\figures\fig_iterative_agent_round_progress.png`
- `paper_draft\figures\fig_iterative_agent_budget_efficiency.pdf`
- `paper_draft\figures\fig_iterative_agent_budget_efficiency.png`

## Claim Boundary

- The agent loop proposes structured candidates only.
- API output, when enabled, is JSON-only, allowlisted, and verifier-checked.
- The committed evaluation uses frozen replay by default and does not refit real-data models.
- Final split metrics are post-selection descriptive only.
- The result is evidence about proposal refinement and candidate-budget efficiency.
