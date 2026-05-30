# API-Assisted Structured Proposal Evaluation

This report summarizes an optional API-assisted structured candidate proposal check.
The API layer is disabled or skipped when credentials are absent. API output is accepted only as JSON,
restricted to an explicit allowlist, and passed through the same verifier before any use.
It cannot create model code and does not run new forecasting experiments.

## Status

- Status: `completed`.
- External API used: `True`.
- Skip reason: ``.

## Metrics

| api_run_status | proposal_count | valid_proposal_count | valid_proposal_rate | duplicate_rate | family_diversity | observation_label_diversity | top_epsilon_useful_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| completed | 10 | 10 | 1.0000 | 0.0000 | 4 | 2 | 1.0000 |

## Verified Candidate Records

| candidate_id | family | model_name | observation_label | delay_label | valid | reasons | top_epsilon_any_series |
| --- | --- | --- | --- | --- | --- | --- | --- |
| c1 | structured_search | constrained_structure_discovery | lagged | 1.0000 | True | nan | True |
| c2 | ablation | exhaustive_structure_discovery | direct | 0.0000 | True | nan | True |
| c3 | ablation | random_structure_discovery | lagged | 1.0000 | True | nan | True |
| c4 | ablation | validation_only_structure_selection | lagged | 1.0000 | True | nan | True |
| c5 | ablation | no_observation_search_discovery | direct | 0.0000 | True | nan | True |
| c6 | mechanistic_baseline | delayed_observation_seir | lagged | nan | True | nan | True |
| c7 | mechanistic_baseline | deterministic_seir | direct | nan | True | nan | True |
| c8 | forecasting_baseline | arima_auto_small | nan | nan | True | nan | True |
| c9 | forecasting_baseline | last_observed | nan | nan | True | nan | True |
| c10 | forecasting_baseline | rolling_mean_4wk | nan | nan | True | nan | True |

## Caveats

- This is proposal-quality evaluation over frozen compact summaries, not a model performance experiment.
- Tests use deterministic mock responses and do not require API credentials.
- Any real API output is constrained by JSON parsing, allowlists, and verifier checks.
