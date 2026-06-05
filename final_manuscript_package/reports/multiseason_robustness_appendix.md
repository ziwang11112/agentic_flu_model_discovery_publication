# Multi-Season Robustness Appendix

This appendix is a compact robustness check for the frozen discovery-ablation paper package.
It does not replace the main frozen benchmark and does not make a FluSight, SOTA, or transfer-forecasting claim.

## Data Scope

- Source dataset: CDC RESP-NET dataset `kvib-3txy`, filtered/transformed to FluSurv-NET hospitalization rates.
- Attribution: Centers for Disease Control and Prevention, RESP-NET/FluSurv-NET.
- Completed seasons included: 2018-19, 2019-20, 2021-22, 2022-23, 2023-24, 2024-25.
- Excluded seasons: `2020-21` because required age strata are incomplete; `2025-26` because it is preliminary.
- Age groups evaluated: Overall, 0-4 yr, >= 65 yr.

## Evaluation Design

Each completed season is evaluated as its own within-season trajectory with chronological train/validation/test splits.
This is not previous-season-to-future-season transfer forecasting. Structure selection uses train/validation evidence only;
test and rolling-origin metrics are used for post-selection evaluation and appendix interpretation.

## Model Set And Budget

- Models: last_observed, rolling_mean_4wk, arima_auto_small, deterministic_seir, delayed_observation_seir, constrained_structure_discovery, no_observation_search_discovery, validation_only_structure_selection.
- Horizons: 1.
- Reduced fitting budget: n_restarts=1, rolling_n_restarts=0, maxiter=25.
- Discovery budget: beam_width=2, max_rounds=2, exhaustive_max_candidates=10, allow_truncated_exhaustive=True.

## Key Finding

For `0-4 yr`, the compact multi-season check reports: mixed season-dependent evidence.
A positive constrained-vs-no-observation rolling delta means the observation-aware constrained discovery model
had lower rolling mean absolute error than the no-observation-search ablation for that season/age stratum.

## Recommendation Modes By Age Group

| age_group | num_seasons | recommended_model_mode | recommended_model_frequency | constrained_discovery_recommended_count | delayed_I_selected_count | positive_observation_search_delta_count |
| --- | --- | --- | --- | --- | --- | --- |
| 0-4 yr | 6 | no_observation_search_discovery | 0.3333 | 0 | 0 | 1 |
| >= 65 yr | 6 | arima_auto_small | 0.6667 | 0 | 3 | 4 |
| Overall | 6 | arima_auto_small | 0.5000 | 1 | 1 | 3 |

## Season-Level Recommendations

| season | age_group | recommended_model | decision_type | best_test_model | best_rolling_model |
| --- | --- | --- | --- | --- | --- |
| 2018-19 | 0-4 yr | no_observation_search_discovery | balanced_tradeoff | validation_only_structure_selection | arima_auto_small |
| 2018-19 | >= 65 yr | arima_auto_small | stability_preferred | rolling_mean_4wk | arima_auto_small |
| 2018-19 | Overall | arima_auto_small | stability_preferred | rolling_mean_4wk | arima_auto_small |
| 2019-20 | 0-4 yr | deterministic_seir | balanced_tradeoff | validation_only_structure_selection | arima_auto_small |
| 2019-20 | >= 65 yr | arima_auto_small | stability_preferred | constrained_structure_discovery | arima_auto_small |
| 2019-20 | Overall | constrained_structure_discovery | test_preferred | constrained_structure_discovery | arima_auto_small |
| 2021-22 | 0-4 yr | arima_auto_small | stability_preferred | rolling_mean_4wk | arima_auto_small |
| 2021-22 | >= 65 yr | arima_auto_small | stability_preferred | rolling_mean_4wk | arima_auto_small |
| 2021-22 | Overall | rolling_mean_4wk | test_preferred | rolling_mean_4wk | arima_auto_small |
| 2022-23 | 0-4 yr | rolling_mean_4wk | stability_preferred | delayed_observation_seir | rolling_mean_4wk |
| 2022-23 | >= 65 yr | arima_auto_small | consensus | arima_auto_small | arima_auto_small |
| 2022-23 | Overall | arima_auto_small | stability_preferred | rolling_mean_4wk | arima_auto_small |
| 2023-24 | 0-4 yr | arima_auto_small | consensus | arima_auto_small | arima_auto_small |
| 2023-24 | >= 65 yr | no_observation_search_discovery | balanced_tradeoff | constrained_structure_discovery | arima_auto_small |
| 2023-24 | Overall | deterministic_seir | balanced_tradeoff | delayed_observation_seir | arima_auto_small |
| 2024-25 | 0-4 yr | no_observation_search_discovery | balanced_tradeoff | deterministic_seir | arima_auto_small |
| 2024-25 | >= 65 yr | deterministic_seir | balanced_tradeoff | constrained_structure_discovery | arima_auto_small |
| 2024-25 | Overall | arima_auto_small | stability_preferred | deterministic_seir | arima_auto_small |

## Observation Map Frequencies

| season | age_group | model_name | structure_name | observation_map | delay_weeks | score_policy |
| --- | --- | --- | --- | --- | --- | --- |
| 2018-19 | 0-4 yr | constrained_structure_discovery | SEIHR | H | 0.0000 | stability_aware |
| 2018-19 | 0-4 yr | no_observation_search_discovery | SEIRS | I | 0.0000 | stability_aware |
| 2018-19 | 0-4 yr | validation_only_structure_selection | SEIAR | I | 0.0000 | validation_only |
| 2018-19 | >= 65 yr | constrained_structure_discovery | SEIR | delayed_I | 3.0000 | stability_aware |
| 2018-19 | >= 65 yr | no_observation_search_discovery | SEIR | I | 0.0000 | stability_aware |
| 2018-19 | >= 65 yr | validation_only_structure_selection | SEIAR | I | 0.0000 | validation_only |
| 2018-19 | Overall | constrained_structure_discovery | SEIHR | H | 0.0000 | stability_aware |
| 2018-19 | Overall | no_observation_search_discovery | SEIR | I | 0.0000 | stability_aware |
| 2018-19 | Overall | validation_only_structure_selection | SEIAR | delayed_I | 1.0000 | validation_only |
| 2019-20 | 0-4 yr | constrained_structure_discovery | SEIR | I | 0.0000 | stability_aware |
| 2019-20 | 0-4 yr | no_observation_search_discovery | SEIAR | I | 0.0000 | stability_aware |
| 2019-20 | 0-4 yr | validation_only_structure_selection | SEIAR | delayed_I | 2.0000 | validation_only |
| 2019-20 | >= 65 yr | constrained_structure_discovery | SEIAR | I | 0.0000 | stability_aware |
| 2019-20 | >= 65 yr | no_observation_search_discovery | SEIRS | I | 0.0000 | stability_aware |
| 2019-20 | >= 65 yr | validation_only_structure_selection | SEIHR | H | 0.0000 | validation_only |
| 2019-20 | Overall | constrained_structure_discovery | SEIHR | H | 0.0000 | stability_aware |
| 2019-20 | Overall | no_observation_search_discovery | SIR | I | 0.0000 | stability_aware |
| 2019-20 | Overall | validation_only_structure_selection | SEIAR | delayed_I | 3.0000 | validation_only |
| 2021-22 | 0-4 yr | constrained_structure_discovery | SEIRS | I | 0.0000 | stability_aware |
| 2021-22 | 0-4 yr | no_observation_search_discovery | SEIRS | I | 0.0000 | stability_aware |
| 2021-22 | 0-4 yr | validation_only_structure_selection | SEIAR | delayed_I | 1.0000 | validation_only |
| 2021-22 | >= 65 yr | constrained_structure_discovery | SEIRS | delayed_I | 3.0000 | stability_aware |
| 2021-22 | >= 65 yr | no_observation_search_discovery | SEIRS | I | 0.0000 | stability_aware |
| 2021-22 | >= 65 yr | validation_only_structure_selection | SEIAR | delayed_I | 1.0000 | validation_only |

_Showing 24 of 54 rows._

## Observation-Search Impact By Season

| season | age_group | delta_test_mae | delta_rolling_mean_mae | constrained_structure | constrained_observation_map | no_observation_structure | no_observation_observation_map |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2018-19 | 0-4 yr | -0.4865 | -0.3676 | SEIHR | H | SEIRS | I |
| 2018-19 | >= 65 yr | -1.2639 | 0.0731 | SEIR | delayed_I | SEIR | I |
| 2018-19 | Overall | -0.1731 | -0.0905 | SEIHR | H | SEIR | I |
| 2019-20 | 0-4 yr | -0.1892 | -1.4115 | SEIR | I | SEIAR | I |
| 2019-20 | >= 65 yr | 2.8910 | 1.7863 | SEIAR | I | SEIRS | I |
| 2019-20 | Overall | 2.4785 | 0.1376 | SEIHR | H | SIR | I |
| 2021-22 | 0-4 yr | -0.0002 | 0.0015 | SEIRS | I | SEIRS | I |
| 2021-22 | >= 65 yr | 0.6618 | 0.2159 | SEIRS | delayed_I | SEIRS | I |
| 2021-22 | Overall | -0.0072 | 0.0004 | SIR | I | SIR | I |
| 2022-23 | 0-4 yr | -0.0330 | -0.0191 | SIR | I | SIR | I |
| 2022-23 | >= 65 yr | -0.0011 | 0.0081 | SEIHR | I+H | SIR | I |
| 2022-23 | Overall | 0.0050 | 0.0022 | SIR | delayed_I | SIR | I |
| 2023-24 | 0-4 yr | -0.0172 | -0.0196 | SEIRS | I | SEIRS | I |
| 2023-24 | >= 65 yr | 0.0001 | -0.0436 | SEIR | I | SEIHR | I |
| 2023-24 | Overall | 0.0203 | -0.0148 | SEIR | I | SIR | I |
| 2024-25 | 0-4 yr | 0.0513 | -2.7315 | SEIHR | H | SIR | I |
| 2024-25 | >= 65 yr | 0.0022 | -1.7392 | SEIR | delayed_I | SEIHR | I |
| 2024-25 | Overall | -0.4179 | -2.2547 | SEIHR | H | SIR | I |

## Caveats

- This appendix is reduced-budget robustness evidence, not a new main benchmark freeze.
- It is within-season retrospective evaluation, not FluSight-style prospective forecasting.
- The result should only strengthen the paper if the pediatric observation-aware signal is repeated across seasons;
  otherwise it should be framed as season-dependent evidence.
- Numerical instability flags, if present in compact summaries, should be retained for transparency and not used for positive claims.

## Figures

- `paper_draft/figures/fig_multiseason_recommendation_modes.pdf`
- `paper_draft/figures/fig_multiseason_recommendation_modes.png`
- `paper_draft/figures/fig_multiseason_observation_search_impact.pdf`
- `paper_draft/figures/fig_multiseason_observation_search_impact.png`
