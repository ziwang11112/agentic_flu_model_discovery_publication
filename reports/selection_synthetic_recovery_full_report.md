# Expanded Synthetic Structured Recovery Sweep

This is a generic structured time-series software validation sweep. It uses no real FluSurv-NET
data, runs no real-data forecasting experiments, calls no external API, and does not provide
real-world mechanism-recovery evidence.

## Scope

- Sweep label: expanded_synthetic_structured_recovery_full.
- Tasks: direct_signal, lagged_signal_1, lagged_signal_2, mixture_observation, hidden_component_proxy.
- Seeds: 1..100 (100 seeds).
- Noise levels: [0.0, 0.025, 0.05, 0.1, 0.15].
- Candidate budgets: [3, 5, 10, 20, 40].
- Policies/baselines: pareto_epsilon, weighted_score, hard_veto_decision_tree, deterministic_seed_proposer, random_label_baseline, no_observation_label_baseline.
- API path: disabled.

## Overall Policy Comparison

| policy_name | observation_label_recovery_rate | delay_label_recovery_rate | candidate_family_recovery_rate | mean_rolling_error | budget_to_recover_true_label | valid_proposal_rate | duplicate_proposal_rate | top_epsilon_hit_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deterministic_seed_proposer | 0.8257 | 0.7782 | 0.8257 | 0.0702 | 4.8106 | 1.0000 | 0.0000 | 0.8728 |
| pareto_epsilon | 0.7429 | 0.7470 | 0.7429 | 0.0721 | 4.8277 | 1.0000 | 0.0000 | 0.8504 |
| weighted_score | 0.6781 | 0.6280 | 0.6781 | 0.0735 | 4.8164 | 1.0000 | 0.0000 | 0.7462 |
| hard_veto_decision_tree | 0.5596 | 0.5480 | 0.5596 | 0.0979 | 3.4975 | 1.0000 | 0.0000 | 0.7068 |
| random_label_baseline | 0.2597 | 0.3587 | 0.2597 | 0.1313 | 4.0287 | 1.0000 | 0.0000 | 0.3019 |
| no_observation_label_baseline | 0.2000 | 0.4000 | 0.2000 | 0.1232 | 3.0000 | 1.0000 | 0.0000 | 0.2924 |

## Noise-Stratified Recovery

| policy_name | noise_level | observation_label_recovery_rate | delay_label_recovery_rate | top_epsilon_hit_rate |
| --- | --- | --- | --- | --- |
| deterministic_seed_proposer | 0.0000 | 0.8800 | 0.8400 | 0.8400 |
| deterministic_seed_proposer | 0.0250 | 0.8800 | 0.8400 | 0.8580 |
| deterministic_seed_proposer | 0.0500 | 0.8640 | 0.8240 | 0.8784 |
| deterministic_seed_proposer | 0.1000 | 0.7896 | 0.7400 | 0.8888 |
| deterministic_seed_proposer | 0.1500 | 0.7148 | 0.6472 | 0.8988 |
| hard_veto_decision_tree | 0.0000 | 0.6000 | 0.6000 | 0.5600 |
| hard_veto_decision_tree | 0.0250 | 0.6000 | 0.6000 | 0.6628 |
| hard_veto_decision_tree | 0.0500 | 0.5664 | 0.5616 | 0.7304 |
| hard_veto_decision_tree | 0.1000 | 0.5160 | 0.4860 | 0.7696 |
| hard_veto_decision_tree | 0.1500 | 0.5156 | 0.4924 | 0.8112 |
| no_observation_label_baseline | 0.0000 | 0.2000 | 0.4000 | 0.2000 |
| no_observation_label_baseline | 0.0250 | 0.2000 | 0.4000 | 0.2000 |
| no_observation_label_baseline | 0.0500 | 0.2000 | 0.4000 | 0.2440 |
| no_observation_label_baseline | 0.1000 | 0.2000 | 0.4000 | 0.3680 |
| no_observation_label_baseline | 0.1500 | 0.2000 | 0.4000 | 0.4500 |
| pareto_epsilon | 0.0000 | 0.8800 | 0.9200 | 0.8400 |
| pareto_epsilon | 0.0250 | 0.8080 | 0.8480 | 0.8500 |
| pareto_epsilon | 0.0500 | 0.7264 | 0.7600 | 0.8104 |
| pareto_epsilon | 0.1000 | 0.6800 | 0.6512 | 0.8648 |
| pareto_epsilon | 0.1500 | 0.6200 | 0.5560 | 0.8868 |
| random_label_baseline | 0.0000 | 0.2444 | 0.3388 | 0.1724 |
| random_label_baseline | 0.0250 | 0.2588 | 0.3608 | 0.2248 |
| random_label_baseline | 0.0500 | 0.2280 | 0.3448 | 0.2692 |
| random_label_baseline | 0.1000 | 0.2536 | 0.3568 | 0.3592 |
| random_label_baseline | 0.1500 | 0.3136 | 0.3924 | 0.4840 |
| weighted_score | 0.0000 | 0.7600 | 0.7200 | 0.7200 |
| weighted_score | 0.0250 | 0.7568 | 0.7168 | 0.7356 |
| weighted_score | 0.0500 | 0.6656 | 0.6256 | 0.7040 |
| weighted_score | 0.1000 | 0.6164 | 0.5556 | 0.7604 |
| weighted_score | 0.1500 | 0.5916 | 0.5220 | 0.8112 |

## Budget-Stratified Recovery

| policy_name | budget | observation_label_recovery_rate | delay_label_recovery_rate | top_epsilon_hit_rate |
| --- | --- | --- | --- | --- |
| deterministic_seed_proposer | 3 | 0.5908 | 0.3916 | 0.5640 |
| deterministic_seed_proposer | 5 | 0.7344 | 0.7252 | 0.8000 |
| deterministic_seed_proposer | 10 | 0.9344 | 0.9248 | 1.0000 |
| deterministic_seed_proposer | 20 | 0.9344 | 0.9248 | 1.0000 |
| deterministic_seed_proposer | 40 | 0.9344 | 0.9248 | 1.0000 |
| hard_veto_decision_tree | 3 | 0.5720 | 0.5368 | 0.5416 |
| hard_veto_decision_tree | 5 | 0.5460 | 0.5508 | 0.7376 |
| hard_veto_decision_tree | 10 | 0.5600 | 0.5508 | 0.7516 |
| hard_veto_decision_tree | 20 | 0.5600 | 0.5508 | 0.7516 |
| hard_veto_decision_tree | 40 | 0.5600 | 0.5508 | 0.7516 |
| no_observation_label_baseline | 3 | 0.2000 | 0.4000 | 0.2924 |
| no_observation_label_baseline | 5 | 0.2000 | 0.4000 | 0.2924 |
| no_observation_label_baseline | 10 | 0.2000 | 0.4000 | 0.2924 |
| no_observation_label_baseline | 20 | 0.2000 | 0.4000 | 0.2924 |
| no_observation_label_baseline | 40 | 0.2000 | 0.4000 | 0.2924 |
| pareto_epsilon | 3 | 0.5720 | 0.5368 | 0.5416 |
| pareto_epsilon | 5 | 0.6356 | 0.7720 | 0.7776 |
| pareto_epsilon | 10 | 0.8356 | 0.8088 | 0.9776 |
| pareto_epsilon | 20 | 0.8356 | 0.8088 | 0.9776 |
| pareto_epsilon | 40 | 0.8356 | 0.8088 | 0.9776 |
| random_label_baseline | 3 | 0.2576 | 0.3288 | 0.3128 |
| random_label_baseline | 5 | 0.2692 | 0.3692 | 0.3148 |
| random_label_baseline | 10 | 0.2572 | 0.3652 | 0.2940 |
| random_label_baseline | 20 | 0.2572 | 0.3652 | 0.2940 |
| random_label_baseline | 40 | 0.2572 | 0.3652 | 0.2940 |
| weighted_score | 3 | 0.5908 | 0.3916 | 0.5640 |
| weighted_score | 5 | 0.7128 | 0.7036 | 0.7996 |
| weighted_score | 10 | 0.6956 | 0.6816 | 0.7892 |
| weighted_score | 20 | 0.6956 | 0.6816 | 0.7892 |
| weighted_score | 40 | 0.6956 | 0.6816 | 0.7892 |

## Per-Task Recovery

| task_name | policy_name | observation_label_recovery_rate | delay_label_recovery_rate | mean_rolling_error | top_epsilon_hit_rate |
| --- | --- | --- | --- | --- | --- |
| direct_signal | deterministic_seed_proposer | 0.9456 | 0.9456 | 0.0505 | 1.0000 |
| direct_signal | hard_veto_decision_tree | 1.0000 | 1.0000 | 0.0507 | 1.0000 |
| direct_signal | no_observation_label_baseline | 1.0000 | 1.0000 | 0.0507 | 1.0000 |
| direct_signal | pareto_epsilon | 1.0000 | 1.0000 | 0.0507 | 1.0000 |
| direct_signal | random_label_baseline | 0.4084 | 0.4936 | 0.0916 | 0.4632 |
| direct_signal | weighted_score | 0.9928 | 0.9928 | 0.0507 | 1.0000 |
| hidden_component_proxy | deterministic_seed_proposer | 0.6000 | 0.6012 | 0.1416 | 0.6000 |
| hidden_component_proxy | hard_veto_decision_tree | 0.0420 | 0.2200 | 0.2704 | 0.0420 |
| hidden_component_proxy | no_observation_label_baseline | 0.0000 | 1.0000 | 0.2912 | 0.0000 |
| hidden_component_proxy | pareto_epsilon | 0.6000 | 0.9272 | 0.1460 | 0.6000 |
| hidden_component_proxy | random_label_baseline | 0.0900 | 0.5324 | 0.2649 | 0.0900 |
| hidden_component_proxy | weighted_score | 0.6000 | 0.6016 | 0.1416 | 0.6000 |
| lagged_signal_1 | deterministic_seed_proposer | 0.9124 | 0.8916 | 0.0505 | 1.0000 |
| lagged_signal_1 | hard_veto_decision_tree | 0.2560 | 0.2048 | 0.0579 | 0.7480 |
| lagged_signal_1 | no_observation_label_baseline | 0.0000 | 0.0000 | 0.0817 | 0.1240 |
| lagged_signal_1 | pareto_epsilon | 0.8640 | 0.8640 | 0.0513 | 0.9880 |
| lagged_signal_1 | random_label_baseline | 0.3348 | 0.2084 | 0.0922 | 0.3684 |
| lagged_signal_1 | weighted_score | 0.6892 | 0.6848 | 0.0553 | 0.7804 |
| lagged_signal_2 | deterministic_seed_proposer | 0.9984 | 0.7792 | 0.0566 | 0.8276 |
| lagged_signal_2 | hard_veto_decision_tree | 0.9896 | 0.7968 | 0.0567 | 0.8272 |
| lagged_signal_2 | no_observation_label_baseline | 0.0000 | 0.0000 | 0.1245 | 0.0020 |
| lagged_signal_2 | pareto_epsilon | 0.9960 | 0.6896 | 0.0572 | 0.8256 |
| lagged_signal_2 | random_label_baseline | 0.3276 | 0.2892 | 0.1167 | 0.1752 |
| lagged_signal_2 | weighted_score | 0.9804 | 0.7324 | 0.0571 | 0.8096 |
| mixture_observation | deterministic_seed_proposer | 0.6720 | 0.6736 | 0.0519 | 0.9364 |
| mixture_observation | hard_veto_decision_tree | 0.5104 | 0.5184 | 0.0537 | 0.9168 |
| mixture_observation | no_observation_label_baseline | 0.0000 | 0.0000 | 0.0681 | 0.3360 |
| mixture_observation | pareto_epsilon | 0.2544 | 0.2544 | 0.0553 | 0.8384 |
| mixture_observation | random_label_baseline | 0.1376 | 0.2700 | 0.0910 | 0.4128 |
| mixture_observation | weighted_score | 0.1280 | 0.1284 | 0.0627 | 0.5412 |

## Comparison To Stage 4 Local Sweep

| policy_name | observation_label_recovery_rate_stage4 | observation_label_recovery_rate_stage5 | delay_label_recovery_rate_stage4 | delay_label_recovery_rate_stage5 | top_epsilon_hit_rate_stage4 | top_epsilon_hit_rate_stage5 |
| --- | --- | --- | --- | --- | --- | --- |
| deterministic_seed_proposer | 0.8000 | 0.8257 | 0.7450 | 0.7782 | 0.8350 | 0.8728 |
| hard_veto_decision_tree | 0.5583 | 0.5596 | 0.5450 | 0.5480 | 0.6717 | 0.7068 |
| no_observation_label_baseline | 0.2000 | 0.2000 | 0.4000 | 0.4000 | 0.2800 | 0.2924 |
| pareto_epsilon | 0.7350 | 0.7429 | 0.7550 | 0.7470 | 0.8083 | 0.8504 |
| random_label_baseline | 0.2417 | 0.2597 | 0.3317 | 0.3587 | 0.2483 | 0.3019 |
| weighted_score | 0.6833 | 0.6781 | 0.6250 | 0.6280 | 0.7283 | 0.7462 |

## Go/No-Go Interpretation

- Pareto-epsilon observation recovery is 0.7429, compared with random-label baseline 0.2597 and no-observation-label baseline 0.2000.
- At noise level 0.10, pareto-epsilon observation recovery is 0.6800.
- Deterministic seed proposer observation recovery is 0.8257; when it is stronger or comparable, we do not claim pareto-epsilon is universally best.
- Mixture and proxy tasks remain the hardest conditions and should be described as controlled failure modes, not as real-data mechanism evidence.

## Caveats

- This expanded sweep is synthetic software validation only.
- It does not use real FluSurv-NET data and does not alter the frozen discovery-ablation artifacts.
- It does not evaluate real-world forecasting performance or mechanism recovery.
- API-assisted proposal is disabled.
