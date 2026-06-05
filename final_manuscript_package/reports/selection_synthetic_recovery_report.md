# Synthetic Structured Recovery Evaluation

This is a local deterministic software evaluation over generic structured time-series toy tasks.
It does not call external APIs, does not run new forecasting experiments, and does not provide
biological, medical, operational, or intervention guidance.

## Scope

- Tasks: direct_signal, lagged_signal_1, lagged_signal_2, mixture_observation, hidden_component_proxy.
- Seeds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].
- Noise levels: [0.0, 0.05, 0.1].
- Candidate budgets: [3, 5, 10, 20].
- Policies/baselines: pareto_epsilon, weighted_score, hard_veto_decision_tree, random_label_baseline, no_observation_label_baseline, deterministic_seed_proposer.
- API path: disabled by default.

The tasks are generic structured state-space analogues for direct, lagged, mixture, and proxy
observation labels. They are not mechanism-discovery evidence for the real FluSurv-NET benchmark.

## Policy-Level Recovery

| policy_name | observation_label_recovery_rate | delay_label_recovery_rate | candidate_family_recovery_rate | mean_rolling_error | budget_to_recover_true_label | valid_proposal_rate | duplicate_proposal_rate | top_epsilon_hit_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deterministic_seed_proposer | 0.8000 | 0.7450 | 0.8000 | 0.0651 | 4.7931 | 1.0000 | 0.0000 | 0.8350 |
| hard_veto_decision_tree | 0.5583 | 0.5450 | 0.5583 | 0.0908 | 3.4495 | 1.0000 | 0.0000 | 0.6717 |
| no_observation_label_baseline | 0.2000 | 0.4000 | 0.2000 | 0.1170 | 3.0000 | 1.0000 | 0.0000 | 0.2800 |
| pareto_epsilon | 0.7350 | 0.7550 | 0.7350 | 0.0670 | 4.8125 | 1.0000 | 0.0000 | 0.8083 |
| random_label_baseline | 0.2417 | 0.3317 | 0.2417 | 0.1283 | 3.7407 | 1.0000 | 0.0000 | 0.2483 |
| weighted_score | 0.6833 | 0.6250 | 0.6833 | 0.0681 | 4.7857 | 1.0000 | 0.0000 | 0.7283 |

## Per-Task Recovery

| task_name | policy_name | observation_label_recovery_rate | delay_label_recovery_rate | mean_rolling_error |
| --- | --- | --- | --- | --- |
| direct_signal | deterministic_seed_proposer | 0.9750 | 0.9750 | 0.0385 |
| direct_signal | hard_veto_decision_tree | 1.0000 | 1.0000 | 0.0386 |
| direct_signal | no_observation_label_baseline | 1.0000 | 1.0000 | 0.0386 |
| direct_signal | pareto_epsilon | 1.0000 | 1.0000 | 0.0386 |
| direct_signal | random_label_baseline | 0.3333 | 0.4167 | 0.0843 |
| direct_signal | weighted_score | 1.0000 | 1.0000 | 0.0386 |
| hidden_component_proxy | deterministic_seed_proposer | 0.5000 | 0.5000 | 0.1605 |
| hidden_component_proxy | hard_veto_decision_tree | 0.0167 | 0.2250 | 0.2790 |
| hidden_component_proxy | no_observation_label_baseline | 0.0000 | 1.0000 | 0.2960 |
| hidden_component_proxy | pareto_epsilon | 0.5000 | 0.9000 | 0.1662 |
| hidden_component_proxy | random_label_baseline | 0.0333 | 0.4417 | 0.2818 |
| hidden_component_proxy | weighted_score | 0.5000 | 0.5000 | 0.1605 |
| lagged_signal_1 | deterministic_seed_proposer | 0.9000 | 0.9000 | 0.0385 |
| lagged_signal_1 | hard_veto_decision_tree | 0.2500 | 0.2250 | 0.0466 |
| lagged_signal_1 | no_observation_label_baseline | 0.0000 | 0.0000 | 0.0728 |
| lagged_signal_1 | pareto_epsilon | 0.9000 | 0.9000 | 0.0392 |
| lagged_signal_1 | random_label_baseline | 0.3333 | 0.2417 | 0.0852 |
| lagged_signal_1 | weighted_score | 0.7500 | 0.7500 | 0.0427 |
| lagged_signal_2 | deterministic_seed_proposer | 1.0000 | 0.7250 | 0.0471 |
| lagged_signal_2 | hard_veto_decision_tree | 1.0000 | 0.7500 | 0.0472 |
| lagged_signal_2 | no_observation_label_baseline | 0.0000 | 0.0000 | 0.1188 |
| lagged_signal_2 | pareto_epsilon | 1.0000 | 0.7000 | 0.0472 |
| lagged_signal_2 | random_label_baseline | 0.4250 | 0.3167 | 0.0981 |
| lagged_signal_2 | weighted_score | 1.0000 | 0.7083 | 0.0472 |
| mixture_observation | deterministic_seed_proposer | 0.6250 | 0.6250 | 0.0409 |
| mixture_observation | hard_veto_decision_tree | 0.5250 | 0.5250 | 0.0426 |
| mixture_observation | no_observation_label_baseline | 0.0000 | 0.0000 | 0.0587 |
| mixture_observation | pareto_epsilon | 0.2750 | 0.2750 | 0.0440 |
| mixture_observation | random_label_baseline | 0.0833 | 0.2417 | 0.0923 |
| mixture_observation | weighted_score | 0.1667 | 0.1667 | 0.0513 |

## Budget Curve

| policy_name | budget | observation_label_recovery_rate | delay_label_recovery_rate | top_epsilon_hit_rate |
| --- | --- | --- | --- | --- |
| deterministic_seed_proposer | 3 | 0.6000 | 0.4000 | 0.5400 |
| deterministic_seed_proposer | 5 | 0.7333 | 0.7267 | 0.8000 |
| deterministic_seed_proposer | 10 | 0.9333 | 0.9267 | 1.0000 |
| deterministic_seed_proposer | 20 | 0.9333 | 0.9267 | 1.0000 |
| hard_veto_decision_tree | 3 | 0.5800 | 0.5400 | 0.5133 |
| hard_veto_decision_tree | 5 | 0.5467 | 0.5467 | 0.7200 |
| hard_veto_decision_tree | 10 | 0.5533 | 0.5467 | 0.7267 |
| hard_veto_decision_tree | 20 | 0.5533 | 0.5467 | 0.7267 |
| no_observation_label_baseline | 3 | 0.2000 | 0.4000 | 0.2800 |
| no_observation_label_baseline | 5 | 0.2000 | 0.4000 | 0.2800 |
| no_observation_label_baseline | 10 | 0.2000 | 0.4000 | 0.2800 |
| no_observation_label_baseline | 20 | 0.2000 | 0.4000 | 0.2800 |
| pareto_epsilon | 3 | 0.5800 | 0.5400 | 0.5133 |
| pareto_epsilon | 5 | 0.6533 | 0.8000 | 0.7733 |
| pareto_epsilon | 10 | 0.8533 | 0.8400 | 0.9733 |
| pareto_epsilon | 20 | 0.8533 | 0.8400 | 0.9733 |
| random_label_baseline | 3 | 0.2600 | 0.3067 | 0.2600 |
| random_label_baseline | 5 | 0.2667 | 0.3667 | 0.2800 |
| random_label_baseline | 10 | 0.2200 | 0.3267 | 0.2267 |
| random_label_baseline | 20 | 0.2200 | 0.3267 | 0.2267 |
| weighted_score | 3 | 0.6000 | 0.4000 | 0.5400 |
| weighted_score | 5 | 0.7200 | 0.7133 | 0.8000 |
| weighted_score | 10 | 0.7067 | 0.6933 | 0.7867 |
| weighted_score | 20 | 0.7067 | 0.6933 | 0.7867 |

## Caveats

- This is a local synthetic recovery check, not a real-data forecasting-performance result.
- The toy tasks are deliberately small and deterministic so they can be tested quickly.
- API-assisted proposal is not used unless explicitly enabled in a future config.
- The result should be read as software validation for observation-label and delay-label selection logic.
