# Numerical Failure Audit

This audit summarizes numerical diagnostics from `artifacts_discovery_ablation/benchmark_model_summary.csv`. Models flagged for numerical instability are retained for transparency but should not be used to support positive claims.

## Summary

- Total model-series rows: `108`
- Flagged rows: `11`
- Models with at least one flagged row: `6`
- Full CSV: `artifacts_discovery_ablation/numerical_failure_summary.csv`

## Flagged Models By Count

| model_name | flagged_series_count |
| --- | --- |
| hospitalized_seihr | 5 |
| fractional_seir | 2 |
| deterministic_seir | 1 |
| constrained_structure_discovery | 1 |
| probabilistic_seir | 1 |
| validation_only_structure_selection | 1 |

## Flagged Rows

| series_name | model_name | train_success | train_plus_validation_success | full_success | max_abs_test_prediction | test_mae | rolling_mean_mae |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Overall | hospitalized_seihr | False | False | True | 0.1856 | 0.0361 | 0.0856 |
| Overall | probabilistic_seir | False | True | True | 0.1894 | 0.0368 | 0.0957 |
| 0-4 yr | hospitalized_seihr | True | False | True | 0.2729 | 0.1175 | 0.2117 |
| 18-49 yr | deterministic_seir | False | True | True | 0.0874 | 0.0448 | 0.0735 |
| 18-49 yr | fractional_seir | False | True | True | 0.1166 | 0.0786 | 0.0996 |
| 18-49 yr | hospitalized_seihr | True | False | True | 0.0870 | 0.0447 | 0.0746 |
| 50-64 yr | fractional_seir | False | True | True | 0.2430 | 0.0997 | 0.1251 |
| 50-64 yr | hospitalized_seihr | False | True | True | 0.1315 | 0.0372 | 0.0635 |
| >= 65 yr | constrained_structure_discovery | False | True | True | 0.2619 | 0.1219 | 0.1748 |
| >= 65 yr | hospitalized_seihr | False | True | True | 0.5656 | 0.1295 | 0.2593 |
| >= 65 yr | validation_only_structure_selection | True | False | True | 0.2607 | 0.1223 | 0.1577 |

## Recommended Paper Wording

> Models flagged for numerical instability are retained for transparency but are not used to support positive claims.

## Notes

The flag combines fit success and prediction-scale diagnostics. It does not automatically invalidate a row for descriptive reporting, but it should prevent using that row as evidence for superiority.
