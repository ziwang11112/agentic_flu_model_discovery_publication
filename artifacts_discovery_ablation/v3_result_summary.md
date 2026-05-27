# V3 Result Summary

This report summarizes the current benchmark outputs for the reproducible influenza forecasting pipeline.

## Headline

The current results support age-aware model selection rather than a single globally best model family.

## Overall Series Ranking

| model_name | test_mae | rolling_mean_mae | num_free_params | num_compartments |
| --- | --- | --- | --- | --- |
| delayed_observation_seir | 0.0351 | 0.0814 | 8 | 4 |
| deterministic_seir | 0.0351 | 0.0821 | 8 | 4 |
| hospitalized_seihr | 0.0361 | 0.0856 | 11 | 5 |
| probabilistic_seir | 0.0368 | 0.0957 | 9 | 4 |
| exhaustive_structure_discovery | 0.0370 | 0.0889 | 6 | 3 |
| no_stability_discovery | 0.0370 | 0.0889 | 6 | 3 |
| random_structure_discovery | 0.0370 | 0.0889 | 6 | 3 |
| constrained_structure_discovery | 0.0370 | 0.0889 | 6 | 3 |
| no_observation_search_discovery | 0.0703 | 0.0989 | 10 | 4 |
| validation_only_structure_selection | 0.0748 | 0.0849 | 10 | 4 |
| equal_weight_point_ensemble | 0.0779 | 0.0818 | 0 | 0 |
| fractional_seir | 0.0848 | 0.1356 | 9 | 4 |
| arima_auto_small | 0.1091 | 0.0435 | 0 | 0 |
| last_observed | 0.1091 | 0.0435 | 0 | 0 |
| rolling_mean_2wk | 0.1091 | 0.0588 | 0 | 0 |
| lagged_gradient_boosting | 0.1091 | 0.1022 | 0 | 0 |
| lagged_ridge | 0.1091 | 0.1022 | 0 | 0 |
| rolling_mean_4wk | 0.1091 | 0.1022 | 0 | 0 |

## Age-Group Winners

| series_name | best_test_model | best_test_mae | best_rolling_model | best_rolling_mean_mae |
| --- | --- | --- | --- | --- |
| 0-4 yr | arima_auto_small | 0.0818 | constrained_structure_discovery | 0.1002 |
| 18-49 yr | arima_auto_small | 0.0091 | arima_auto_small | 0.0304 |
| 5-17 yr | rolling_mean_2wk | 0.0000 | no_stability_discovery | 0.0353 |
| 50-64 yr | validation_only_structure_selection | 0.0321 | delayed_observation_seir | 0.0528 |
| >= 65 yr | fractional_seir | 0.1196 | validation_only_structure_selection | 0.1577 |
| Overall | delayed_observation_seir | 0.0351 | arima_auto_small | 0.0435 |

## Recommended Models

| series_name | recommended_model | decision_type | best_test_model | best_rolling_model |
| --- | --- | --- | --- | --- |
| 0-4 yr | constrained_structure_discovery | stability_preferred | arima_auto_small | constrained_structure_discovery |
| 18-49 yr | arima_auto_small | consensus | arima_auto_small | arima_auto_small |
| 5-17 yr | rolling_mean_2wk | balanced_tradeoff | arima_auto_small | no_stability_discovery |
| 50-64 yr | exhaustive_structure_discovery | balanced_tradeoff | validation_only_structure_selection | delayed_observation_seir |
| >= 65 yr | validation_only_structure_selection | stability_preferred | fractional_seir | validation_only_structure_selection |
| Overall | delayed_observation_seir | test_preferred | delayed_observation_seir | arima_auto_small |

## Recommendation Tally

- `arima_auto_small` recommended for 1 series
- `constrained_structure_discovery` recommended for 1 series
- `delayed_observation_seir` recommended for 1 series
- `exhaustive_structure_discovery` recommended for 1 series
- `rolling_mean_2wk` recommended for 1 series
- `validation_only_structure_selection` recommended for 1 series

## Probabilistic Calibration

| series_name | interval_level | empirical_coverage | nominal_coverage | coverage_gap | average_interval_width |
| --- | --- | --- | --- | --- | --- |
| 0-4 yr | 80 | 0.9091 | 0.8000 | 0.1091 | 0.5101 |
| 0-4 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 0.7504 |
| 18-49 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 0.2491 |
| 18-49 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 0.3519 |
| 5-17 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 0.4314 |
| 5-17 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 0.7078 |
| 50-64 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 0.4693 |
| 50-64 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 0.7465 |
| >= 65 yr | 80 | 1.0000 | 0.8000 | 0.2000 | 1.2210 |
| >= 65 yr | 95 | 1.0000 | 0.9500 | 0.0500 | 1.7553 |
| Overall | 80 | 1.0000 | 0.8000 | 0.2000 | 0.4812 |
| Overall | 95 | 1.0000 | 0.9500 | 0.0500 | 0.7536 |

## Interpretation

- `deterministic_seir` remains the strongest default baseline for the overall series and several adult groups.
- `constrained_structure_discovery` is already useful in selected age groups, especially when simpler discovered structures outperform larger hand-specified models.
- `probabilistic_seir` is best interpreted as a stability and uncertainty baseline rather than the primary point-forecast winner.
- The next research step is to strengthen stability-aware selection across multiple validation splits rather than further increasing raw structural flexibility.
