# Result Freeze Manifest

This manifest freezes the discovery ablation result package for paper interpretation and reviewer/rebuttal traceability. It records the exact code and artifact state used for the paper-ready summaries in this branch.

## Commits

- Phase 0/1 implementation commit: `7ef36e574a84e0ceef784ce676ef87b6802d9e75`
- Phase 2/3 implementation commit: `7d8ae4e48bf001ec24daacd413b7f403eb8c4392`
- Result artifact commit: `09c93188e319aa51933f6029260fff2f3a09cd03`
- Paper integration commit: `3608b641dc45ab35a347059ef53567371ce62f1e`
- Branch: `codex-supplemental-experiment-results`

## Main Run

- Main result config: `configs/discovery_ablation.yaml`
- Artifact root: `artifacts_discovery_ablation`
- Main report: `reports/baseline_ablation_report.md`
- Processed data root: `data/processed_discovery_ablation`
- Reference model for paired rolling comparison: `constrained_structure_discovery`

## Key Outputs

- `artifacts_discovery_ablation/benchmark_model_summary.csv`
- `artifacts_discovery_ablation/benchmark_series_winners.csv`
- `artifacts_discovery_ablation/age_group_recommendation.csv`
- `artifacts_discovery_ablation/paired_rolling_error_comparison.csv`
- `artifacts_discovery_ablation/paper_recommendation_table.csv`
- `artifacts_discovery_ablation/discovery_ablation_compact_table.csv`
- `artifacts_discovery_ablation/observation_search_impact_table.csv`
- `artifacts_discovery_ablation/paired_rolling_key_comparisons.csv`
- `artifacts_discovery_ablation/numerical_failure_summary.csv`

## Artifact Inventory

- Model metrics files: `108`
- Leaderboard CSV files: `42`
- Local files under artifact root at freeze time: `871`
- Git-tracked files under artifact root at result commit: `865`

`benchmark_leaderboard_partial.csv` is an ignored intermediate file and is not part of the frozen result claim. The final `benchmark_leaderboard.csv` is tracked.

## Reproduction Commands

```bash
python run_experiment.py --config configs/discovery_ablation.yaml --log-level INFO
python scripts/build_baseline_comparison_report.py --artifact-root artifacts_discovery_ablation --reference constrained_structure_discovery
```

## Scope

This freeze is for evidence distillation and paper narrative. It should not be mixed with new model families, new experiments, or additional baselines unless a new result freeze is created.

## Clean Publication Repository

This repository is a slim publication package derived from the full research branch
`codex-supplemental-experiment-results` in `ziwang11112/agentic_flu_model_discovery`.

The full artifact/history branch remains available in the original repository.
This clean repository keeps compact frozen CSV summaries, paper figures, source code,
tests, configs, and paper reports, but omits old exploratory artifacts and per-model
diagnostic plots/traces.

## Multi-Season Robustness Appendix

The compact multi-season robustness appendix is an add-on check for the paper
discussion. It does not replace the frozen discovery-ablation result above.

- Appendix config: `configs/multiseason_robustness.yaml`
- Appendix artifact root: `artifacts_multiseason_robustness_compact`
- Appendix report: `reports/multiseason_robustness_appendix.md`
- Data source: CDC RESP-NET dataset `kvib-3txy`, transformed to FluSurv-NET rates
- Completed seasons only: `2018-19`, `2019-20`, `2021-22`, `2022-23`, `2023-24`, `2024-25`
- Excluded: incomplete `2020-21`; preliminary `2025-26`

This appendix evaluates each completed season as its own within-season
trajectory. It is reduced-budget robustness evidence, not a FluSight leaderboard
or previous-season-to-future-season transfer-forecasting claim.
