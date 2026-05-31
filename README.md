# agentic_flu_model_discovery_publication

Clean publication package for verifier-gated, evidence-aware cross-family
model selection for partially observed influenza hospitalization-rate
forecasting.

This repository is derived from the full research/archive repository
`ziwang11112/agentic_flu_model_discovery`, but it does not inherit the old Git
history or old exploratory artifact blobs. It preserves the frozen
discovery-ablation evidence package used by the paper draft:

- verifier-gated candidate proposal, selection, and claim-boundary auditing
- opt-in forecasting baselines
- hand-specified epidemic baselines
- constrained observation-aware structure discovery
- random/exhaustive/validation/no-observation/no-stability discovery ablations
- paired rolling-origin comparisons
- compact multi-season robustness appendix
- synthetic structured recovery validation
- optional API-assisted structured proposal smoke outputs
- paper-ready compact result CSVs
- paper figures and LaTeX draft

The full research/archive repository remains the place for older exploratory
runs, LLM traces, smoke outputs, and large diagnostic artifact roots.

## Key Findings

- Across six frozen FluSurv-NET series, no model dominates all strata.
- Observation-aware constrained discovery is most useful for the pediatric
  `0-4 yr` series, where the selected `SEIRS` delayed-observation structure
  improves rolling-origin stability relative to an observation-fixed ablation.
- Adult strata often favor simpler forecasting baselines or hand-specified
  epidemic models.
- Paired rolling-origin comparisons are post-hoc evidence, not model
  selection.
- The repository includes an offline verifier and selection-policy layer for
  claim-boundary auditing over frozen summary tables.
- The expanded synthetic structured recovery sweep supports observation-label
  and delay-label selection logic under controlled toy time-series tasks; it
  is not evidence of real-world mechanism recovery.
- The optional API-assisted proposal smoke is allowlist- and verifier-gated;
  it is proposal-quality evidence, not forecasting-performance evidence.
- Stage 6 candidate execution/replay evaluates proposal ordering under fixed
  budgets; its real-data layer is frozen replay only and does not refit models.
- Stage 7 adds bounded real-data candidate execution with compact outputs and
  no mutation of the frozen discovery-ablation artifacts.
- Numerical failure flags are retained for transparency and are not used to
  support positive claims.

## Repository Layout

```text
configs/                         publication and smoke configs
src/                             benchmark, baseline, discovery, evaluation code
tests/                           compact tests for the frozen package
scripts/build_baseline_comparison_report.py
scripts/build_paper_figures.py
artifacts_discovery_ablation/    compact frozen CSV/JSON/Markdown summaries
artifacts_multiseason_robustness_compact/
                                 compact appendix-only multi-season summaries
paper_draft/                     LaTeX draft and generated figures
reports/                         freeze, interpretation, audit, and figure reports
```

## Frozen Result Provenance

- Main config: `configs/discovery_ablation.yaml`
- Artifact root: `artifacts_discovery_ablation`
- Main report: `reports/baseline_ablation_report.md`
- Result artifact commit in the archive repo:
  `09c93188e319aa51933f6029260fff2f3a09cd03`
- Paper integration commit in the archive repo:
  `3608b641dc45ab35a347059ef53567371ce62f1e`

See also:

- `PUBLICATION_PACKAGE.md`
- `DATA_AVAILABILITY.md`
- `reports/reference_matrix.md`
- `reports/result_freeze_manifest.md`
- `reports/discovery_ablation_interpretation.md`
- `reports/numerical_failure_audit.md`
- `reports/paper_figure_index.md`

## Reproduce The Frozen Package

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the full frozen discovery-ablation benchmark:

```bash
python run_experiment.py --config configs/discovery_ablation.yaml --log-level INFO
```

Rebuild the compact comparison report from benchmark artifacts:

```bash
python scripts/build_baseline_comparison_report.py --artifact-root artifacts_discovery_ablation --reference constrained_structure_discovery
```

Rebuild paper figures from compact frozen CSV artifacts:

```bash
python scripts/build_paper_figures.py
```

Run the compact multi-season robustness appendix:

```bash
python scripts/run_multiseason_robustness.py --config configs/multiseason_robustness.yaml --log-level INFO
python scripts/build_multiseason_robustness_report.py --artifact-root artifacts_multiseason_robustness_compact
```

The multi-season appendix uses CDC RESP-NET dataset `kvib-3txy`, transformed to
FluSurv-NET hospitalization rates. It uses completed seasons only, excludes
`2020-21` because required age strata are incomplete, and excludes `2025-26`
because it is preliminary. Each completed season is evaluated as its own
within-season trajectory; this is not a transfer-forecasting benchmark. Users
should cite CDC/RESP-NET and verify redistribution terms before making
derivative packages public. See `DATA_AVAILABILITY.md` for source attribution,
included raw and compact derived files, and report/figure regeneration
commands.

Run tests:

```bash
python -m pytest
```

## Paper Draft

The LaTeX draft lives under `paper_draft/`. If a TeX distribution is available:

```bash
cd paper_draft
latexmk -pdf main.tex
```

Generated paper figures are kept in both PDF and PNG form under
`paper_draft/figures/`.

## Scope Notes

This package is intentionally narrow. It is not a FluSight leaderboard claim,
does not include FluSight/Flusion/SINDy comparisons, and does not claim that
discovery is globally best. The current evidence supports age-aware and
objective-aware model recommendation under a controlled grammar and budget.
The multi-season appendix is reduced-budget robustness evidence for the
observation-aware discovery signal, not a replacement for the frozen main
benchmark.
