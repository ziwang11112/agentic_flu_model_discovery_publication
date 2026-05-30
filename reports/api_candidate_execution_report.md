# Verifier-Gated API/Mock Candidate Execution Replay

This Stage 6 evaluation measures proposal ordering and candidate-budget efficiency. The synthetic layer
uses generic toy tasks with deterministic scoring. The real-data layer is replay-only over frozen compact
summary rows. No real-data model refitting is performed, no external API is called in the committed config,
and API/mock output cannot generate or execute model code.

## Scope

- External API used: False.
- Synthetic rows: 216.
- Frozen replay rows: 24.
- Prompt audit rows: 20.
- Prompt audit passed: True.
- Test metrics are post-hoc descriptive only in frozen replay rows.
- Real-data refitting is deferred to an optional Stage 6b.

## Summary Metrics

| layer | proposer_type | observation_label_recovery_rate | delay_label_recovery_rate | top_epsilon_hit_rate | best_rolling_error_after_k | best_rolling_score_after_k | post_selection_test_mae | valid_proposal_rate | duplicate_rate | out_of_allowlist_rejection_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| synthetic_execution | deterministic_seed_proposer | 1.0000 | 0.8333 | 0.8333 | 0.0261 |  |  | 1.0000 | 0.0000 | 0.0000 |
| synthetic_execution | exhaustive_oracle | 1.0000 | 1.0000 | 1.0000 | 0.0186 |  |  | 1.0000 | 0.0000 | 0.0000 |
| synthetic_execution | failure_guided_proposer | 1.0000 | 1.0000 | 1.0000 | 0.0186 |  |  | 1.0000 | 0.0000 | 0.0000 |
| synthetic_execution | mock_api_proposer | 1.0000 | 1.0000 | 1.0000 | 0.0186 |  |  | 1.0000 | 0.0000 | 0.0000 |
| synthetic_execution | no_observation_label_baseline | 0.5000 | 0.5000 | 0.5000 | 0.0667 |  |  | 1.0000 | 0.0000 | 0.0000 |
| synthetic_execution | random_candidate_proposer | 1.0000 | 0.9444 | 0.9444 | 0.0210 |  |  | 1.0000 | 0.0000 | 0.0000 |
| frozen_replay | deterministic_seed_proposer |  |  | 0.6667 |  | 0.0857 | 0.0966 | 1.0000 | 0.0000 | 0.0000 |
| frozen_replay | mock_api_proposer |  |  | 1.0000 |  | 0.0718 | 0.0988 | 1.0000 | 0.0000 | 0.0000 |
| frozen_replay | oracle_full_candidate_ranking |  |  | 1.0000 |  | 0.0718 | 0.0988 | 1.0000 | 0.0000 | 0.0000 |
| frozen_replay | random_candidate_proposer |  |  | 0.6667 |  | 0.0845 | 0.0741 | 1.0000 | 0.0000 | 0.0000 |

## Budget Curves

| layer | proposer_type | budget | observation_label_recovery_rate | best_rolling_score_after_k | top_epsilon_hit_rate |
| --- | --- | --- | --- | --- | --- |
| synthetic_execution | deterministic_seed_proposer | 3 | 1.0000 |  | 0.5000 |
| synthetic_execution | deterministic_seed_proposer | 5 | 1.0000 |  | 1.0000 |
| synthetic_execution | deterministic_seed_proposer | 10 | 1.0000 |  | 1.0000 |
| synthetic_execution | exhaustive_oracle | 3 | 1.0000 |  | 1.0000 |
| synthetic_execution | exhaustive_oracle | 5 | 1.0000 |  | 1.0000 |
| synthetic_execution | exhaustive_oracle | 10 | 1.0000 |  | 1.0000 |
| synthetic_execution | failure_guided_proposer | 3 | 1.0000 |  | 1.0000 |
| synthetic_execution | failure_guided_proposer | 5 | 1.0000 |  | 1.0000 |
| synthetic_execution | failure_guided_proposer | 10 | 1.0000 |  | 1.0000 |
| synthetic_execution | mock_api_proposer | 3 | 1.0000 |  | 1.0000 |
| synthetic_execution | mock_api_proposer | 5 | 1.0000 |  | 1.0000 |
| synthetic_execution | mock_api_proposer | 10 | 1.0000 |  | 1.0000 |
| synthetic_execution | no_observation_label_baseline | 3 | 0.5000 |  | 0.5000 |
| synthetic_execution | no_observation_label_baseline | 5 | 0.5000 |  | 0.5000 |
| synthetic_execution | no_observation_label_baseline | 10 | 0.5000 |  | 0.5000 |
| synthetic_execution | random_candidate_proposer | 3 | 1.0000 |  | 0.8333 |
| synthetic_execution | random_candidate_proposer | 5 | 1.0000 |  | 1.0000 |
| synthetic_execution | random_candidate_proposer | 10 | 1.0000 |  | 1.0000 |
| frozen_replay | deterministic_seed_proposer | 3 |  | 0.0926 | 0.5000 |
| frozen_replay | deterministic_seed_proposer | 5 |  | 0.0926 | 0.5000 |
| frozen_replay | deterministic_seed_proposer | 10 |  | 0.0718 | 1.0000 |
| frozen_replay | mock_api_proposer | 3 |  | 0.0718 | 1.0000 |
| frozen_replay | mock_api_proposer | 5 |  | 0.0718 | 1.0000 |
| frozen_replay | mock_api_proposer | 10 |  | 0.0718 | 1.0000 |
| frozen_replay | oracle_full_candidate_ranking | 3 |  | 0.0718 | 1.0000 |
| frozen_replay | oracle_full_candidate_ranking | 5 |  | 0.0718 | 1.0000 |
| frozen_replay | oracle_full_candidate_ranking | 10 |  | 0.0718 | 1.0000 |
| frozen_replay | random_candidate_proposer | 3 |  | 0.0908 | 0.5000 |
| frozen_replay | random_candidate_proposer | 5 |  | 0.0908 | 0.5000 |
| frozen_replay | random_candidate_proposer | 10 |  | 0.0718 | 1.0000 |

## Synthetic Execution

| task_name | proposer_type | budget | observation_label_recovered | delay_label_recovered | top_epsilon_hit | best_rolling_error_after_k |
| --- | --- | --- | --- | --- | --- | --- |
| direct_signal | mock_api_proposer | 3 | True | True | True | 0.0000 |
| direct_signal | mock_api_proposer | 5 | True | True | True | 0.0000 |
| direct_signal | mock_api_proposer | 10 | True | True | True | 0.0000 |
| direct_signal | deterministic_seed_proposer | 3 | True | True | True | 0.0000 |
| direct_signal | deterministic_seed_proposer | 5 | True | True | True | 0.0000 |
| direct_signal | deterministic_seed_proposer | 10 | True | True | True | 0.0000 |
| direct_signal | random_candidate_proposer | 3 | True | True | True | 0.0000 |
| direct_signal | random_candidate_proposer | 5 | True | True | True | 0.0000 |
| direct_signal | random_candidate_proposer | 10 | True | True | True | 0.0000 |
| direct_signal | failure_guided_proposer | 3 | True | True | True | 0.0000 |
| direct_signal | failure_guided_proposer | 5 | True | True | True | 0.0000 |
| direct_signal | failure_guided_proposer | 10 | True | True | True | 0.0000 |
| direct_signal | no_observation_label_baseline | 3 | True | True | True | 0.0000 |
| direct_signal | no_observation_label_baseline | 5 | True | True | True | 0.0000 |
| direct_signal | no_observation_label_baseline | 10 | True | True | True | 0.0000 |
| direct_signal | exhaustive_oracle | 3 | True | True | True | 0.0000 |
| direct_signal | exhaustive_oracle | 5 | True | True | True | 0.0000 |
| direct_signal | exhaustive_oracle | 10 | True | True | True | 0.0000 |
| direct_signal | mock_api_proposer | 3 | True | True | True | 0.0324 |
| direct_signal | mock_api_proposer | 5 | True | True | True | 0.0324 |
| direct_signal | mock_api_proposer | 10 | True | True | True | 0.0324 |
| direct_signal | deterministic_seed_proposer | 3 | True | True | True | 0.0324 |
| direct_signal | deterministic_seed_proposer | 5 | True | True | True | 0.0324 |
| direct_signal | deterministic_seed_proposer | 10 | True | True | True | 0.0324 |
| direct_signal | random_candidate_proposer | 3 | True | True | True | 0.0324 |
| direct_signal | random_candidate_proposer | 5 | True | True | True | 0.0324 |
| direct_signal | random_candidate_proposer | 10 | True | True | True | 0.0324 |
| direct_signal | failure_guided_proposer | 3 | True | True | True | 0.0324 |
| direct_signal | failure_guided_proposer | 5 | True | True | True | 0.0324 |
| direct_signal | failure_guided_proposer | 10 | True | True | True | 0.0324 |
| direct_signal | no_observation_label_baseline | 3 | True | True | True | 0.0324 |
| direct_signal | no_observation_label_baseline | 5 | True | True | True | 0.0324 |
| direct_signal | no_observation_label_baseline | 10 | True | True | True | 0.0324 |
| direct_signal | exhaustive_oracle | 3 | True | True | True | 0.0324 |
| direct_signal | exhaustive_oracle | 5 | True | True | True | 0.0324 |
| direct_signal | exhaustive_oracle | 10 | True | True | True | 0.0324 |

_Showing 36 of 216 rows._

## Frozen Real-Data Replay

| series_name | proposer_type | budget | selected_model_at_k | best_rolling_score_after_k | post_selection_test_mae | test_metric_usage |
| --- | --- | --- | --- | --- | --- | --- |
| Overall | mock_api_proposer | 3 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | mock_api_proposer | 5 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | mock_api_proposer | 10 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | deterministic_seed_proposer | 3 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | deterministic_seed_proposer | 5 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | deterministic_seed_proposer | 10 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | random_candidate_proposer | 3 | delayed_observation_seir | 0.0814 | 0.0351 | posthoc_descriptive_only |
| Overall | random_candidate_proposer | 5 | delayed_observation_seir | 0.0814 | 0.0351 | posthoc_descriptive_only |
| Overall | random_candidate_proposer | 10 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | oracle_full_candidate_ranking | 3 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | oracle_full_candidate_ranking | 5 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| Overall | oracle_full_candidate_ranking | 10 | arima_auto_small | 0.0435 | 0.1091 | posthoc_descriptive_only |
| 0-4 yr | mock_api_proposer | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | mock_api_proposer | 5 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | mock_api_proposer | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 3 | arima_auto_small | 0.1417 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 5 | arima_auto_small | 0.1417 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 5 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | oracle_full_candidate_ranking | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | oracle_full_candidate_ranking | 5 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |
| 0-4 yr | oracle_full_candidate_ranking | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | posthoc_descriptive_only |

## No-Leakage Prompt Audit

| series_name | proposer_type | prompt_contains_test_metric | prompt_contains_test_winner | prompt_contains_posthoc_metric | safe_prompt_passed |
| --- | --- | --- | --- | --- | --- |
| direct_signal | mock_api_proposer | False | False | False | True |
| direct_signal | deterministic_seed_proposer | False | False | False | True |
| direct_signal | random_candidate_proposer | False | False | False | True |
| direct_signal | failure_guided_proposer | False | False | False | True |
| direct_signal | no_observation_label_baseline | False | False | False | True |
| direct_signal | exhaustive_oracle | False | False | False | True |
| lagged_signal_2 | mock_api_proposer | False | False | False | True |
| lagged_signal_2 | deterministic_seed_proposer | False | False | False | True |
| lagged_signal_2 | random_candidate_proposer | False | False | False | True |
| lagged_signal_2 | failure_guided_proposer | False | False | False | True |
| lagged_signal_2 | no_observation_label_baseline | False | False | False | True |
| lagged_signal_2 | exhaustive_oracle | False | False | False | True |
| Overall | mock_api_proposer | False | False | False | True |
| Overall | deterministic_seed_proposer | False | False | False | True |
| Overall | random_candidate_proposer | False | False | False | True |
| Overall | oracle_full_candidate_ranking | False | False | False | True |
| 0-4 yr | mock_api_proposer | False | False | False | True |
| 0-4 yr | deterministic_seed_proposer | False | False | False | True |
| 0-4 yr | random_candidate_proposer | False | False | False | True |
| 0-4 yr | oracle_full_candidate_ranking | False | False | False | True |

## Claim Boundary

- This supports proposal-quality and candidate-budget-efficiency claims only.
- It does not support forecasting-performance, state-of-the-art, mechanism-discovery, or autonomous-science claims.
- Synthetic execution uses generic structured time-series tasks.
- Frozen real-data replay uses existing compact rows and does not refit models.
