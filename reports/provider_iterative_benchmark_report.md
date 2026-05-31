# Cross-Provider Iterative Proposer Benchmark

This Stage 9 report evaluates provider backends only as constrained structured candidate proposers.
All provider outputs are JSON/schema parsed, allowlisted, verifier-checked, and audited before replay.
The benchmark is not a forecasting-performance benchmark, FluSight leaderboard, clinical benchmark,
autonomous-science claim, or real-world mechanism-discovery claim.

## Scope

- Series: ['Overall', '0-4 yr', '5-17 yr', '18-49 yr', '50-64 yr', '>= 65 yr'].
- Repeats: 3.
- Rounds: 3.
- Candidates per round: 3.
- Budgets: [3, 6, 9].
- Real providers run: 4.
- Required providers for cross-provider evidence: 2.
- Sufficient for cross-provider comparison: True.
- Prompt/no-leakage audit passed: True.
- Claim audit passed: True.
- Bounded union execution run: False.

## Provider Status

| provider_name | model_name | available | ran | skip_reason |
| --- | --- | --- | --- | --- |
| openai_gpt | gpt-5.4-mini | True | True |  |
| anthropic_claude | claude-sonnet-4-6 | True | True |  |
| google_gemini | gemini-2.5-flash | True | True |  |
| deepseek | deepseek-v4-flash | True | True |  |

## Proposal Validity And Diversity

| provider_name | model_name | proposer_type | schema_parse_success_rate | valid_proposal_rate | out_of_allowlist_rejection_rate | duplicate_rate | claim_safety_violation_rate | family_diversity | observation_label_diversity | delay_label_diversity | top_epsilon_hit_rate | mean_best_rolling_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_iterative | 1.0000 | 0.7840 | 0.0000 | 0.2160 | 0.0000 | 2.5741 | 1.6852 | 0.6852 | 0.7778 | 0.0822 |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_single_shot | 0.9815 | 0.9020 | 0.0556 | 0.0980 | 0.0000 | 3.7778 | 2.3889 | 1.4444 | 0.7778 | 0.0815 |
| deepseek | deepseek-v4-flash | deepseek_iterative | 1.0000 | 0.8333 | 0.0000 | 0.1667 | 0.0000 | 2.7037 | 1.8519 | 0.9259 | 0.8333 | 0.0798 |
| deepseek | deepseek-v4-flash | deepseek_single_shot | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4.0000 | 2.7222 | 1.8333 | 1.0000 | 0.0723 |
| deterministic_baseline | deterministic | deterministic_seed_proposer | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2.6667 | 1.9444 | 1.0000 | 0.7778 | 0.0813 |
| deterministic_baseline | deterministic | failure_guided_proposer | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 2.7222 | 2.0556 | 1.1667 | 0.8333 | 0.0790 |
| deterministic_baseline | deterministic | oracle_reference | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.0000 | 2.3889 | 1.5000 | 1.0000 | 0.0723 |
| deterministic_baseline | deterministic | random_candidate_proposer | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 3.3333 | 2.3889 | 1.6111 | 0.7222 | 0.0829 |
| google_gemini | gemini-2.5-flash | google_gemini_iterative | 0.2037 | 1.0000 | 0.7963 | 0.0000 | 0.0000 | 0.4630 | 0.4630 | 0.0000 | 0.2222 | 0.1165 |
| google_gemini | gemini-2.5-flash | google_gemini_single_shot | 0.2593 | 1.0000 | 0.9091 | 0.0000 | 0.0000 | 0.8889 | 0.6111 | 0.3889 | 0.2222 | 0.1055 |
| openai_gpt | gpt-5.4-mini | openai_gpt_iterative | 1.0000 | 0.9198 | 0.0000 | 0.0802 | 0.0000 | 2.6667 | 1.8333 | 0.8519 | 0.7778 | 0.0813 |
| openai_gpt | gpt-5.4-mini | openai_gpt_single_shot | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 4.0000 | 2.7222 | 1.8889 | 0.8889 | 0.0753 |

## Frozen Replay By Budget

| provider_name | model_name | proposer_type | series_name | repeat_idx | budget | selected_model_at_budget | best_rolling_score_at_budget | post_selection_test_mae | top_epsilon_hit | budget_to_top_epsilon | selection_metric_source | test_metric_usage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| openai_gpt | gpt-5.4-mini | openai_gpt_iterative | Overall | 0 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_iterative | Overall | 0 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_iterative | Overall | 0 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_iterative | Overall | 1 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_iterative | Overall | 1 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_iterative | Overall | 1 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_iterative | Overall | 2 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_iterative | Overall | 2 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_iterative | Overall | 2 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_single_shot | Overall | 0 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_single_shot | Overall | 0 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_single_shot | Overall | 0 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_single_shot | Overall | 1 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_single_shot | Overall | 1 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_single_shot | Overall | 1 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_single_shot | Overall | 2 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_single_shot | Overall | 2 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| openai_gpt | gpt-5.4-mini | openai_gpt_single_shot | Overall | 2 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_iterative | Overall | 0 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_iterative | Overall | 0 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_iterative | Overall | 0 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_iterative | Overall | 1 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_iterative | Overall | 1 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_iterative | Overall | 1 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_iterative | Overall | 2 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_iterative | Overall | 2 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_iterative | Overall | 2 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_single_shot | Overall | 0 | 3 |  |  |  | False |  | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_single_shot | Overall | 0 | 6 |  |  |  | False |  | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_single_shot | Overall | 0 | 9 |  |  |  | False |  | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_single_shot | Overall | 1 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_single_shot | Overall | 1 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_single_shot | Overall | 1 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_single_shot | Overall | 2 | 3 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_single_shot | Overall | 2 | 6 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |
| anthropic_claude | claude-sonnet-4-6 | anthropic_claude_single_shot | Overall | 2 | 9 | arima_auto_small | 0.0435 | 0.1091 | True | 3.0000 | rolling_mean_mae | posthoc_descriptive_only |

_Showing 36 of 504 rows._

## Stability By Repeat

| provider_name | proposer_type | series_name | between_repeat_jaccard_overlap | selected_model_agreement_rate | repeat_count |
| --- | --- | --- | --- | --- | --- |
| openai_gpt | openai_gpt_iterative | Overall | 0.9259 | 1.0000 | 3 |
| openai_gpt | openai_gpt_single_shot | Overall | 1.0000 | 1.0000 | 3 |
| anthropic_claude | anthropic_claude_iterative | Overall | 1.0000 | 1.0000 | 3 |
| anthropic_claude | anthropic_claude_single_shot | Overall | 0.2963 | 0.3333 | 3 |
| google_gemini | google_gemini_iterative | Overall | 1.0000 | 1.0000 | 3 |
| google_gemini | google_gemini_single_shot | Overall | 1.0000 | 1.0000 | 3 |
| deepseek | deepseek_iterative | Overall | 0.8426 | 1.0000 | 3 |
| deepseek | deepseek_single_shot | Overall | 0.8667 | 1.0000 | 3 |
| deterministic_baseline | deterministic_seed_proposer | Overall | 1.0000 | 1.0000 | 1 |
| deterministic_baseline | random_candidate_proposer | Overall | 1.0000 | 1.0000 | 1 |
| deterministic_baseline | failure_guided_proposer | Overall | 1.0000 | 1.0000 | 1 |
| deterministic_baseline | oracle_reference | Overall | 1.0000 | 1.0000 | 1 |
| openai_gpt | openai_gpt_iterative | 0-4 yr | 0.8426 | 1.0000 | 3 |
| openai_gpt | openai_gpt_single_shot | 0-4 yr | 1.0000 | 1.0000 | 3 |
| anthropic_claude | anthropic_claude_iterative | 0-4 yr | 1.0000 | 1.0000 | 3 |
| anthropic_claude | anthropic_claude_single_shot | 0-4 yr | 1.0000 | 1.0000 | 3 |
| google_gemini | google_gemini_iterative | 0-4 yr | 1.0000 | 1.0000 | 3 |
| google_gemini | google_gemini_single_shot | 0-4 yr | 0.3333 | 0.3333 | 3 |
| deepseek | deepseek_iterative | 0-4 yr | 0.9167 | 1.0000 | 3 |
| deepseek | deepseek_single_shot | 0-4 yr | 0.8667 | 1.0000 | 3 |
| deterministic_baseline | deterministic_seed_proposer | 0-4 yr | 1.0000 | 1.0000 | 1 |
| deterministic_baseline | random_candidate_proposer | 0-4 yr | 1.0000 | 1.0000 | 1 |
| deterministic_baseline | failure_guided_proposer | 0-4 yr | 1.0000 | 1.0000 | 1 |
| deterministic_baseline | oracle_reference | 0-4 yr | 1.0000 | 1.0000 | 1 |
| openai_gpt | openai_gpt_iterative | 5-17 yr | 0.7185 | 1.0000 | 3 |
| openai_gpt | openai_gpt_single_shot | 5-17 yr | 1.0000 | 1.0000 | 3 |
| anthropic_claude | anthropic_claude_iterative | 5-17 yr | 1.0000 | 1.0000 | 3 |
| anthropic_claude | anthropic_claude_single_shot | 5-17 yr | 1.0000 | 1.0000 | 3 |
| google_gemini | google_gemini_iterative | 5-17 yr | 0.3333 | 0.3333 | 3 |
| google_gemini | google_gemini_single_shot | 5-17 yr | 1.0000 | 1.0000 | 3 |

_Showing 30 of 72 rows._

## Cost And Latency

| provider_name | model_name | latency_seconds_mean | estimated_cost_usd_total | request_count |
| --- | --- | --- | --- | --- |
| anthropic_claude | claude-sonnet-4-6 | 24.2128 | 0 | 108 |
| deepseek | deepseek-v4-flash | 10.9240 | 0 | 108 |
| google_gemini | gemini-2.5-flash | 14.5298 | 0 | 108 |
| openai_gpt | gpt-5.4-mini | 5.0804 | 0 | 108 |

## No-Leakage Audit

| provider_name | model_name | repeat_idx | series_name | proposer_type | round_idx | prompt_contains_test_metric | prompt_contains_test_winner | prompt_contains_test_rank | prompt_contains_posthoc_metric | feedback_contains_test_metric | selection_uses_test_metric | posthoc_test_metric_only | safe_prompt_passed | safe_feedback_passed | safe_selection_passed | allowlist_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| openai_gpt | gpt-5.4-mini | 0 | Overall | openai_gpt_iterative | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 0 | Overall | openai_gpt_iterative | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 0 | Overall | openai_gpt_iterative | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 1 | Overall | openai_gpt_iterative | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 1 | Overall | openai_gpt_iterative | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 1 | Overall | openai_gpt_iterative | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 2 | Overall | openai_gpt_iterative | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 2 | Overall | openai_gpt_iterative | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 2 | Overall | openai_gpt_iterative | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 0 | Overall | openai_gpt_single_shot | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 0 | Overall | openai_gpt_single_shot | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 0 | Overall | openai_gpt_single_shot | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 1 | Overall | openai_gpt_single_shot | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 1 | Overall | openai_gpt_single_shot | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 1 | Overall | openai_gpt_single_shot | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 2 | Overall | openai_gpt_single_shot | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 2 | Overall | openai_gpt_single_shot | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| openai_gpt | gpt-5.4-mini | 2 | Overall | openai_gpt_single_shot | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 0 | Overall | anthropic_claude_iterative | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 0 | Overall | anthropic_claude_iterative | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 0 | Overall | anthropic_claude_iterative | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 1 | Overall | anthropic_claude_iterative | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 1 | Overall | anthropic_claude_iterative | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 1 | Overall | anthropic_claude_iterative | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 2 | Overall | anthropic_claude_iterative | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 2 | Overall | anthropic_claude_iterative | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 2 | Overall | anthropic_claude_iterative | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 0 | Overall | anthropic_claude_single_shot | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 0 | Overall | anthropic_claude_single_shot | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 0 | Overall | anthropic_claude_single_shot | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 1 | Overall | anthropic_claude_single_shot | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 1 | Overall | anthropic_claude_single_shot | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 1 | Overall | anthropic_claude_single_shot | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 2 | Overall | anthropic_claude_single_shot | 1 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 2 | Overall | anthropic_claude_single_shot | 2 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |
| anthropic_claude | claude-sonnet-4-6 | 2 | Overall | anthropic_claude_single_shot | 3 | False | False | False | False | False | False | True | True | True | True | d9d74325ea4070ea |

_Showing 36 of 504 rows._

## Provider-Union Bounded Execution

_No rows._

## Figures

- `paper_draft\figures\fig_provider_validity_diversity.pdf`
- `paper_draft\figures\fig_provider_validity_diversity.png`
- `paper_draft\figures\fig_provider_budget_efficiency.pdf`
- `paper_draft\figures\fig_provider_budget_efficiency.png`
- `paper_draft\figures\fig_provider_round_progress.pdf`
- `paper_draft\figures\fig_provider_round_progress.png`

## Claim Boundary

- Providers are interchangeable structured proposer backends.
- No provider output generates or executes model code.
- Held-out test metrics are excluded from prompts and selection evidence.
- Frozen replay supports proposal ordering and budget-efficiency evidence only.
- Provider-union bounded execution, when enabled, remains bounded and does not imply SOTA.
