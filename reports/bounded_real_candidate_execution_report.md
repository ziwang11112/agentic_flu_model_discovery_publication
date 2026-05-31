# Bounded Real Candidate Execution Evaluation

This Stage 7 report summarizes verifier-gated proposal ordering and bounded candidate execution.
It supports candidate-budget-efficiency claims only. It is not a FluSight leaderboard, SOTA,
autonomous-science, mechanism-discovery, or operational forecasting-performance result.

## Scope

- External API used: False.
- API statuses: ['api_disabled'].
- Unique real-data model executions: 32.
- Frozen replay rows: 96.
- Bounded execution rows: 60.
- No-leakage audit rows: 52.
- Prompt audit passed: True.
- Selection audit passed: True.
- Temporary artifacts removed: True.
- Test metric usage: posthoc_descriptive_only.

## Real API Repeated Frozen Replay

| series_name | proposer_type | valid_proposal_rate | duplicate_rate | out_of_allowlist_rejection_rate | claim_safety_violation_rate | family_diversity | observation_label_diversity | top_epsilon_hit_rate | budget_to_top_epsilon | between_run_jaccard_overlap | selected_model_agreement_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Overall | deterministic_seed_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2.3333 | 1.6667 | 1.0000 | 3.0000 | 1.0000 | 1.0000 |
| Overall | random_candidate_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.2667 | 2.3333 | 0.6000 | 6.6000 | 0.3833 | 1.0000 |
| Overall | failure_guided_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.0000 | 2.0000 | 1.0000 | 3.0000 | 1.0000 | 1.0000 |
| Overall | oracle_full_candidate_ranking | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.0000 | 2.0000 | 1.0000 | 3.0000 | 1.0000 | 1.0000 |
| 0-4 yr | deterministic_seed_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2.3333 | 1.6667 | 0.3333 | 10.0000 | 1.0000 | 1.0000 |
| 0-4 yr | random_candidate_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.3333 | 2.7333 | 0.8667 | 3.8000 | 0.4917 | 1.0000 |
| 0-4 yr | failure_guided_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.6667 | 3.0000 | 1.0000 | 3.0000 | 1.0000 | 1.0000 |
| 0-4 yr | oracle_full_candidate_ranking | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.0000 | 2.3333 | 1.0000 | 3.0000 | 1.0000 | 1.0000 |
| 18-49 yr | deterministic_seed_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2.3333 | 1.6667 | 1.0000 | 3.0000 | 1.0000 | 1.0000 |
| 18-49 yr | random_candidate_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.0667 | 2.2667 | 0.9333 | 3.4000 | 0.6250 | 1.0000 |
| 18-49 yr | failure_guided_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.0000 | 2.0000 | 1.0000 | 3.0000 | 1.0000 | 1.0000 |
| 18-49 yr | oracle_full_candidate_ranking | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.0000 | 2.3333 | 1.0000 | 3.0000 | 1.0000 | 1.0000 |
| >= 65 yr | deterministic_seed_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2.3333 | 1.6667 | 0.3333 | 10.0000 | 1.0000 | 1.0000 |
| >= 65 yr | random_candidate_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.2667 | 2.2667 | 0.5333 | 4.8000 | 0.4000 | 1.0000 |
| >= 65 yr | failure_guided_proposer | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.0000 | 2.0000 | 0.3333 | 5.0000 | 1.0000 | 1.0000 |
| >= 65 yr | oracle_full_candidate_ranking | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.0000 | 2.3333 | 1.0000 | 3.0000 | 1.0000 | 1.0000 |

## Bounded Real-Data Execution

| proposer_type | top_epsilon_hit_rate | mean_rolling_score | mean_post_selection_test_mae | mean_budget_to_top_epsilon | candidate_failure_rate | valid_proposal_rate | duplicate_rate | out_of_allowlist_rejection_rate | claim_safety_violation_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deterministic_seed_proposer | 1.0000 | 0.0978 | 0.1318 | 3.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| failure_guided_proposer | 1.0000 | 0.0966 | 0.1325 | 3.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| mock_api_proposer | 1.0000 | 0.0978 | 0.1318 | 3.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| oracle_full_candidate_ranking | 1.0000 | 0.0978 | 0.1318 | 3.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| random_candidate_proposer | 0.7500 | 0.1152 | 0.1294 | 5.2500 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |

## Selected Models By Proposer/Budget

| series_name | proposer_type | budget | selected_model_at_k | selection_metric_source | validation_or_rolling_score_at_k | post_selection_test_mae | test_metric_usage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | deterministic_seed_proposer | 3 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 5 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | deterministic_seed_proposer | 10 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 3 | rolling_mean_4wk | rolling_mean_mae | 0.1636 | 0.1023 | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 5 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | random_candidate_proposer | 10 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | failure_guided_proposer | 3 | constrained_structure_discovery | rolling_mean_mae | 0.1148 | 0.0905 | posthoc_descriptive_only |
| 0-4 yr | failure_guided_proposer | 5 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | failure_guided_proposer | 10 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | mock_api_proposer | 3 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | mock_api_proposer | 5 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | mock_api_proposer | 10 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | oracle_full_candidate_ranking | 3 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | oracle_full_candidate_ranking | 5 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 0-4 yr | oracle_full_candidate_ranking | 10 | arima_auto_small | rolling_mean_mae | 0.1292 | 0.0818 | posthoc_descriptive_only |
| 18-49 yr | deterministic_seed_proposer | 3 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | deterministic_seed_proposer | 5 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | deterministic_seed_proposer | 10 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | random_candidate_proposer | 3 | last_observed | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | random_candidate_proposer | 5 | last_observed | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | random_candidate_proposer | 10 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | failure_guided_proposer | 3 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | failure_guided_proposer | 5 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | failure_guided_proposer | 10 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | mock_api_proposer | 3 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | mock_api_proposer | 5 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | mock_api_proposer | 10 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | oracle_full_candidate_ranking | 3 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | oracle_full_candidate_ranking | 5 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| 18-49 yr | oracle_full_candidate_ranking | 10 | arima_auto_small | rolling_mean_mae | 0.0318 | 0.0091 | posthoc_descriptive_only |
| Overall | deterministic_seed_proposer | 3 | arima_auto_small | rolling_mean_mae | 0.0319 | 0.1091 | posthoc_descriptive_only |
| Overall | deterministic_seed_proposer | 5 | arima_auto_small | rolling_mean_mae | 0.0319 | 0.1091 | posthoc_descriptive_only |
| Overall | deterministic_seed_proposer | 10 | arima_auto_small | rolling_mean_mae | 0.0319 | 0.1091 | posthoc_descriptive_only |
| Overall | random_candidate_proposer | 3 | last_observed | rolling_mean_mae | 0.0319 | 0.1091 | posthoc_descriptive_only |
| Overall | random_candidate_proposer | 5 | arima_auto_small | rolling_mean_mae | 0.0319 | 0.1091 | posthoc_descriptive_only |
| Overall | random_candidate_proposer | 10 | arima_auto_small | rolling_mean_mae | 0.0319 | 0.1091 | posthoc_descriptive_only |

_Showing 36 of 60 rows._

## Replay By Run

| layer | series_name | proposer_type | repeat_idx | budget | selected_model_at_k | rolling_score_at_k | post_selection_test_mae | top_epsilon_hit | budget_to_top_epsilon | valid_proposal_rate | duplicate_rate | out_of_allowlist_rejection_rate | claim_safety_violation_rate | family_diversity | observation_label_diversity | api_status | evidence_mode | selection_metric_source | test_metric_usage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frozen_replay_repeated | Overall | deterministic_seed_proposer | 0 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1 | 1 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | deterministic_seed_proposer | 0 | 5 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2 | 1 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | deterministic_seed_proposer | 0 | 10 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 0 | 3 | last_observed | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 0 | 5 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 0 | 10 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 1 | 3 | deterministic_seir | 0.0821 | 0.0351 | False | 10 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 1 | 5 | delayed_observation_seir | 0.0814 | 0.0351 | False | 10 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 1 | 10 | arima_auto_small | 0.0435 | 0.1091 | True | 10 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 2 | 3 | constrained_structure_discovery | 0.0889 | 0.0370 | False | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2 | 1 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 2 | 5 | arima_auto_small | 0.0435 | 0.1091 | True | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 2 | 10 | arima_auto_small | 0.0435 | 0.1091 | True | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 3 | 3 | deterministic_seir | 0.0821 | 0.0351 | False | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 3 | 5 | last_observed | 0.0435 | 0.1091 | True | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 3 | 10 | arima_auto_small | 0.0435 | 0.1091 | True | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 4 | 3 | delayed_observation_seir | 0.0814 | 0.0351 | False | 10 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 4 | 5 | delayed_observation_seir | 0.0814 | 0.0351 | False | 10 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | random_candidate_proposer | 4 | 10 | arima_auto_small | 0.0435 | 0.1091 | True | 10 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | failure_guided_proposer | 0 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2 | 1 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | failure_guided_proposer | 0 | 5 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | failure_guided_proposer | 0 | 10 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | oracle_full_candidate_ranking | 0 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2 | 1 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | oracle_full_candidate_ranking | 0 | 5 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | Overall | oracle_full_candidate_ranking | 0 | 10 | arima_auto_small | 0.0435 | 0.1091 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | deterministic_seed_proposer | 0 | 3 | arima_auto_small | 0.1417 | 0.0818 | False | 10 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1 | 1 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | deterministic_seed_proposer | 0 | 5 | arima_auto_small | 0.1417 | 0.0818 | False | 10 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2 | 1 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | deterministic_seed_proposer | 0 | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 10 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 0 | 3 | no_observation_search_discovery | 0.1575 | 0.0911 | False | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 2 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 0 | 5 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 0 | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 1 | 3 | last_observed | 0.1417 | 0.0818 | False | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2 | 1 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 1 | 5 | random_structure_discovery | 0.1007 | 0.0885 | True | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 1 | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 2 | 3 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 2 | 5 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 2 | 10 | constrained_structure_discovery | 0.1002 | 0.0885 | True | 3 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4 | 3 |  | frozen_replay | rolling_mean_mae | posthoc_descriptive_only |

_Showing 36 of 96 rows._

## No-Leakage Audit

| layer | series_name | proposer_type | repeat_idx | prompt_contains_test_metric | prompt_contains_test_winner | prompt_contains_posthoc_metric | selection_uses_test_metric | posthoc_test_metric_only | safe_prompt_passed | safe_selection_passed | allowlist_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frozen_replay_repeated | Overall | deterministic_seed_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | Overall | random_candidate_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | Overall | random_candidate_proposer | 1 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | Overall | random_candidate_proposer | 2 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | Overall | random_candidate_proposer | 3 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | Overall | random_candidate_proposer | 4 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | Overall | failure_guided_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | Overall | oracle_full_candidate_ranking | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 0-4 yr | deterministic_seed_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 1 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 2 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 3 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 0-4 yr | random_candidate_proposer | 4 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 0-4 yr | failure_guided_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 0-4 yr | oracle_full_candidate_ranking | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 18-49 yr | deterministic_seed_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 18-49 yr | random_candidate_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 18-49 yr | random_candidate_proposer | 1 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 18-49 yr | random_candidate_proposer | 2 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 18-49 yr | random_candidate_proposer | 3 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 18-49 yr | random_candidate_proposer | 4 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 18-49 yr | failure_guided_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | 18-49 yr | oracle_full_candidate_ranking | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | >= 65 yr | deterministic_seed_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | >= 65 yr | random_candidate_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | >= 65 yr | random_candidate_proposer | 1 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | >= 65 yr | random_candidate_proposer | 2 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | >= 65 yr | random_candidate_proposer | 3 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | >= 65 yr | random_candidate_proposer | 4 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | >= 65 yr | failure_guided_proposer | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| frozen_replay_repeated | >= 65 yr | oracle_full_candidate_ranking | 0 | False | False | False | False | True | True | True | d9d74325ea4070ea |
| bounded_real_execution | 0-4 yr | deterministic_seed_proposer | 0 | False | False | False | False | True | True | True | 63c118b35bf6ba91 |
| bounded_real_execution | 0-4 yr | random_candidate_proposer | 0 | False | False | False | False | True | True | True | 63c118b35bf6ba91 |
| bounded_real_execution | 0-4 yr | failure_guided_proposer | 0 | False | False | False | False | True | True | True | 63c118b35bf6ba91 |
| bounded_real_execution | 0-4 yr | mock_api_proposer | 0 | False | False | False | False | True | True | True | 63c118b35bf6ba91 |

_Showing 36 of 52 rows._

## Figures

- `paper_draft\figures\fig_bounded_real_execution_budget.pdf`
- `paper_draft\figures\fig_bounded_real_execution_budget.png`
- `paper_draft\figures\fig_real_api_replay_stability.pdf`
- `paper_draft\figures\fig_real_api_replay_stability.png`

## Claim Boundary

- API output, when enabled, is JSON-only, allowlisted, and verifier-gated.
- The real-data layer executes only deterministic repository code.
- Held-out test MAE is post-selection descriptive only.
- Frozen discovery-ablation artifacts are read-only inputs and are not modified.
- Per-model temporary artifacts are removed before committing compact outputs.
