# Verifier-Gated API/Mock Candidate Execution Replay

This Stage 6 evaluation measures proposal ordering and candidate-budget efficiency. The synthetic layer
uses generic toy tasks with deterministic scoring. The real-data layer is replay-only over frozen compact
summary rows. No real-data model refitting is performed, no external API is called in the committed config,
and API/mock output cannot generate or execute model code.

## Scope

- External API used: False.
- Synthetic rows: 24000.
- Frozen replay rows: 64.
- Prompt audit rows: 46.
- Prompt audit passed: True.
- Test metrics are post-hoc descriptive only in frozen replay rows.
- Real-data refitting is deferred to an optional Stage 6b.

## Summary Metrics

| layer | proposer_type | observation_label_recovery_rate | delay_label_recovery_rate | top_epsilon_hit_rate | best_rolling_error_after_k | best_rolling_score_after_k | post_selection_test_mae | valid_proposal_rate | duplicate_rate | out_of_allowlist_rejection_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| synthetic_execution | deterministic_seed_proposer | 0.7863 | 0.7278 | 0.8452 | 0.0825 |  |  | 1.0000 | 0.0000 | 0.0000 |
| synthetic_execution | exhaustive_oracle | 0.9190 | 0.9070 | 1.0000 | 0.0585 |  |  | 1.0000 | 0.0000 | 0.0000 |
| synthetic_execution | failure_guided_proposer | 0.9233 | 0.9113 | 1.0000 | 0.0585 |  |  | 1.0000 | 0.0000 | 0.0000 |
| synthetic_execution | mock_api_proposer | 0.9313 | 0.9190 | 1.0000 | 0.0586 |  |  | 1.0000 | 0.0000 | 0.0000 |
| synthetic_execution | no_observation_label_baseline | 0.2000 | 0.4000 | 0.3210 | 0.1283 |  |  | 1.0000 | 0.0000 | 0.0000 |
| synthetic_execution | random_candidate_proposer | 0.8207 | 0.7943 | 0.9045 | 0.0692 |  |  | 1.0000 | 0.0000 | 0.0000 |
| frozen_replay | deterministic_seed_proposer |  |  | 0.7500 |  | 0.0949 | 0.1070 | 1.0000 | 0.0000 | 0.0000 |
| frozen_replay | mock_api_proposer |  |  | 1.0000 |  | 0.0851 | 0.0822 | 1.0000 | 0.0000 | 0.0000 |
| frozen_replay | oracle_full_candidate_ranking |  |  | 1.0000 |  | 0.0830 | 0.0822 | 1.0000 | 0.0000 | 0.0000 |
| frozen_replay | random_candidate_proposer |  |  | 0.8125 |  | 0.0925 | 0.0752 | 1.0000 | 0.0000 | 0.0000 |

## Budget Curves

| layer | proposer_type | budget | observation_label_recovery_rate | best_rolling_score_after_k | top_epsilon_hit_rate |
| --- | --- | --- | --- | --- | --- |
| synthetic_execution | deterministic_seed_proposer | 3 | 0.5880 |  | 0.5810 |
| synthetic_execution | deterministic_seed_proposer | 5 | 0.7190 |  | 0.8000 |
| synthetic_execution | deterministic_seed_proposer | 10 | 0.9190 |  | 1.0000 |
| synthetic_execution | deterministic_seed_proposer | 20 | 0.9190 |  | 1.0000 |
| synthetic_execution | exhaustive_oracle | 3 | 0.9190 |  | 1.0000 |
| synthetic_execution | exhaustive_oracle | 5 | 0.9190 |  | 1.0000 |
| synthetic_execution | exhaustive_oracle | 10 | 0.9190 |  | 1.0000 |
| synthetic_execution | exhaustive_oracle | 20 | 0.9190 |  | 1.0000 |
| synthetic_execution | failure_guided_proposer | 3 | 0.9360 |  | 1.0000 |
| synthetic_execution | failure_guided_proposer | 5 | 0.9190 |  | 1.0000 |
| synthetic_execution | failure_guided_proposer | 10 | 0.9190 |  | 1.0000 |
| synthetic_execution | failure_guided_proposer | 20 | 0.9190 |  | 1.0000 |
| synthetic_execution | mock_api_proposer | 3 | 0.9680 |  | 1.0000 |
| synthetic_execution | mock_api_proposer | 5 | 0.9190 |  | 1.0000 |
| synthetic_execution | mock_api_proposer | 10 | 0.9190 |  | 1.0000 |
| synthetic_execution | mock_api_proposer | 20 | 0.9190 |  | 1.0000 |
| synthetic_execution | no_observation_label_baseline | 3 | 0.2000 |  | 0.3210 |
| synthetic_execution | no_observation_label_baseline | 5 | 0.2000 |  | 0.3210 |
| synthetic_execution | no_observation_label_baseline | 10 | 0.2000 |  | 0.3210 |
| synthetic_execution | no_observation_label_baseline | 20 | 0.2000 |  | 0.3210 |
| synthetic_execution | random_candidate_proposer | 3 | 0.6120 |  | 0.6990 |
| synthetic_execution | random_candidate_proposer | 5 | 0.8330 |  | 0.9190 |
| synthetic_execution | random_candidate_proposer | 10 | 0.9190 |  | 1.0000 |
| synthetic_execution | random_candidate_proposer | 20 | 0.9190 |  | 1.0000 |
| frozen_replay | deterministic_seed_proposer | 3 |  | 0.1069 | 0.5000 |
| frozen_replay | deterministic_seed_proposer | 5 |  | 0.1069 | 0.5000 |
| frozen_replay | deterministic_seed_proposer | 10 |  | 0.0830 | 1.0000 |
| frozen_replay | deterministic_seed_proposer | 20 |  | 0.0830 | 1.0000 |
| frozen_replay | mock_api_proposer | 3 |  | 0.0872 | 1.0000 |
| frozen_replay | mock_api_proposer | 5 |  | 0.0872 | 1.0000 |
| frozen_replay | mock_api_proposer | 10 |  | 0.0830 | 1.0000 |
| frozen_replay | mock_api_proposer | 20 |  | 0.0830 | 1.0000 |
| frozen_replay | oracle_full_candidate_ranking | 3 |  | 0.0830 | 1.0000 |
| frozen_replay | oracle_full_candidate_ranking | 5 |  | 0.0830 | 1.0000 |
| frozen_replay | oracle_full_candidate_ranking | 10 |  | 0.0830 | 1.0000 |
| frozen_replay | oracle_full_candidate_ranking | 20 |  | 0.0830 | 1.0000 |

_Showing 36 of 40 rows._

## Synthetic Execution

| task_name | proposer_type | budget | observation_label_recovered | delay_label_recovered | top_epsilon_hit | best_rolling_error_after_k |
| --- | --- | --- | --- | --- | --- | --- |
| direct_signal | mock_api_proposer | 3 | True | True | True | 0.0000 |
| direct_signal | mock_api_proposer | 5 | True | True | True | 0.0000 |
| direct_signal | mock_api_proposer | 10 | True | True | True | 0.0000 |
| direct_signal | mock_api_proposer | 20 | True | True | True | 0.0000 |
| direct_signal | deterministic_seed_proposer | 3 | True | True | True | 0.0000 |
| direct_signal | deterministic_seed_proposer | 5 | True | True | True | 0.0000 |
| direct_signal | deterministic_seed_proposer | 10 | True | True | True | 0.0000 |
| direct_signal | deterministic_seed_proposer | 20 | True | True | True | 0.0000 |
| direct_signal | random_candidate_proposer | 3 | True | True | True | 0.0000 |
| direct_signal | random_candidate_proposer | 5 | True | True | True | 0.0000 |
| direct_signal | random_candidate_proposer | 10 | True | True | True | 0.0000 |
| direct_signal | random_candidate_proposer | 20 | True | True | True | 0.0000 |
| direct_signal | failure_guided_proposer | 3 | True | True | True | 0.0000 |
| direct_signal | failure_guided_proposer | 5 | True | True | True | 0.0000 |
| direct_signal | failure_guided_proposer | 10 | True | True | True | 0.0000 |
| direct_signal | failure_guided_proposer | 20 | True | True | True | 0.0000 |
| direct_signal | no_observation_label_baseline | 3 | True | True | True | 0.0000 |
| direct_signal | no_observation_label_baseline | 5 | True | True | True | 0.0000 |
| direct_signal | no_observation_label_baseline | 10 | True | True | True | 0.0000 |
| direct_signal | no_observation_label_baseline | 20 | True | True | True | 0.0000 |
| direct_signal | exhaustive_oracle | 3 | True | True | True | 0.0000 |
| direct_signal | exhaustive_oracle | 5 | True | True | True | 0.0000 |
| direct_signal | exhaustive_oracle | 10 | True | True | True | 0.0000 |
| direct_signal | exhaustive_oracle | 20 | True | True | True | 0.0000 |
| direct_signal | mock_api_proposer | 3 | True | True | True | 0.0324 |
| direct_signal | mock_api_proposer | 5 | True | True | True | 0.0324 |
| direct_signal | mock_api_proposer | 10 | True | True | True | 0.0324 |
| direct_signal | mock_api_proposer | 20 | True | True | True | 0.0324 |
| direct_signal | deterministic_seed_proposer | 3 | True | True | True | 0.0324 |
| direct_signal | deterministic_seed_proposer | 5 | True | True | True | 0.0324 |
| direct_signal | deterministic_seed_proposer | 10 | True | True | True | 0.0324 |
| direct_signal | deterministic_seed_proposer | 20 | True | True | True | 0.0324 |
| direct_signal | random_candidate_proposer | 3 | True | True | True | 0.0324 |
| direct_signal | random_candidate_proposer | 5 | True | True | True | 0.0324 |
| direct_signal | random_candidate_proposer | 10 | True | True | True | 0.0324 |
| direct_signal | random_candidate_proposer | 20 | True | True | True | 0.0324 |

_Showing 36 of 24000 rows._

## Frozen Real-Data Replay

| series_name | proposer_type | budget | selected_model_at_k | best_rolling_score_after_k | post_selection_test_mae | test_metric_usage |
| --- | --- | --- | --- | --- | --- | --- |
| Overall | mock_api_proposer | 3 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | mock_api_proposer | 5 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | mock_api_proposer | 10 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | mock_api_proposer | 20 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | deterministic_seed_proposer | 3 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | deterministic_seed_proposer | 5 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | deterministic_seed_proposer | 10 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | deterministic_seed_proposer | 20 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | random_candidate_proposer | 3 | delayed_observation_seir | 0.0814 | 0.0351 | posthoc_descriptive_only |
| Overall | random_candidate_proposer | 5 | delayed_observation_seir | 0.0814 | 0.0351 | posthoc_descriptive_only |
| Overall | random_candidate_proposer | 10 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | random_candidate_proposer | 20 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | oracle_full_candidate_ranking | 3 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | oracle_full_candidate_ranking | 5 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | oracle_full_candidate_ranking | 10 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | oracle_full_candidate_ranking | 20 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| 0-4 yr | mock_api_proposer | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | mock_api_proposer | 5 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | mock_api_proposer | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | mock_api_proposer | 20 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 3 | arima_auto_small | 0.1417 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 5 | arima_auto_small | 0.1417 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 20 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 5 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 20 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | oracle_full_candidate_ranking | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | oracle_full_candidate_ranking | 5 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | oracle_full_candidate_ranking | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | oracle_full_candidate_ranking | 20 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 18-49 yr | mock_api_proposer | 3 | arima_auto_small | 0.0304 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | mock_api_proposer | 5 | arima_auto_small | 0.0304 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | mock_api_proposer | 10 | arima_auto_small | 0.0304 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | mock_api_proposer | 20 | arima_auto_small | 0.0304 | 0.0091 | posthoc_descriptive_only |

_Showing 36 of 64 rows._

## No-Leakage Prompt Audit

| series_name | proposer_type | prompt_contains_test_metric | prompt_contains_test_winner | prompt_contains_posthoc_metric | safe_prompt_passed |
| --- | --- | --- | --- | --- | --- |
| direct_signal | mock_api_proposer | False | False | False | True |
| direct_signal | deterministic_seed_proposer | False | False | False | True |
| direct_signal | random_candidate_proposer | False | False | False | True |
| direct_signal | failure_guided_proposer | False | False | False | True |
| direct_signal | no_observation_label_baseline | False | False | False | True |
| direct_signal | exhaustive_oracle | False | False | False | True |
| lagged_signal_1 | mock_api_proposer | False | False | False | True |
| lagged_signal_1 | deterministic_seed_proposer | False | False | False | True |
| lagged_signal_1 | random_candidate_proposer | False | False | False | True |
| lagged_signal_1 | failure_guided_proposer | False | False | False | True |
| lagged_signal_1 | no_observation_label_baseline | False | False | False | True |
| lagged_signal_1 | exhaustive_oracle | False | False | False | True |
| lagged_signal_2 | mock_api_proposer | False | False | False | True |
| lagged_signal_2 | deterministic_seed_proposer | False | False | False | True |
| lagged_signal_2 | random_candidate_proposer | False | False | False | True |
| lagged_signal_2 | failure_guided_proposer | False | False | False | True |
| lagged_signal_2 | no_observation_label_baseline | False | False | False | True |
| lagged_signal_2 | exhaustive_oracle | False | False | False | True |
| mixture_observation | mock_api_proposer | False | False | False | True |
| mixture_observation | deterministic_seed_proposer | False | False | False | True |
| mixture_observation | random_candidate_proposer | False | False | False | True |
| mixture_observation | failure_guided_proposer | False | False | False | True |
| mixture_observation | no_observation_label_baseline | False | False | False | True |
| mixture_observation | exhaustive_oracle | False | False | False | True |
| hidden_component_proxy | mock_api_proposer | False | False | False | True |
| hidden_component_proxy | deterministic_seed_proposer | False | False | False | True |
| hidden_component_proxy | random_candidate_proposer | False | False | False | True |
| hidden_component_proxy | failure_guided_proposer | False | False | False | True |
| hidden_component_proxy | no_observation_label_baseline | False | False | False | True |
| hidden_component_proxy | exhaustive_oracle | False | False | False | True |
| Overall | mock_api_proposer | False | False | False | True |
| Overall | deterministic_seed_proposer | False | False | False | True |
| Overall | random_candidate_proposer | False | False | False | True |
| Overall | oracle_full_candidate_ranking | False | False | False | True |
| 0-4 yr | mock_api_proposer | False | False | False | True |
| 0-4 yr | deterministic_seed_proposer | False | False | False | True |

_Showing 36 of 46 rows._

## Claim Boundary

- This supports proposal-quality and candidate-budget-efficiency claims only.
- It does not support forecasting-performance, state-of-the-art, mechanism-discovery, or autonomous-science claims.
- Synthetic execution uses generic structured time-series tasks.
- Frozen real-data replay uses existing compact rows and does not refit models.
