# Data Availability

This repository is a clean publication package derived from the full research archive. It includes the raw CSV inputs and compact derived summaries needed to reproduce the paper figures and reports. Users should verify CDC/RESP-NET source terms before public redistribution or before creating derivative public packages.

## Source Attribution

The influenza hospitalization data are derived from CDC FluSurv-NET / RESP-NET sources, including the CDC RESP-NET dataset identified in this package as `kvib-3txy` for the multi-season appendix. Please cite CDC/RESP-NET and the FluSurv-NET surveillance source when using these data.

Related attribution files:

- `paper_draft/references.bib`
- `reports/reference_matrix.md`
- `PUBLICATION_PACKAGE.md`

## Raw Data Included

The package includes:

- `data/raw/FluSurveillance_Custom_Download_Data.csv`
- `data/raw/flusurvnet_multiseason_full.csv`

The multi-season appendix uses completed seasons only: `2018-19`, `2019-20`, `2021-22`, `2022-23`, `2023-24`, and `2024-25`. It excludes incomplete `2020-21` and preliminary `2025-26` from paper-level claims.

## Processed Inputs Included

The package includes lightweight processed inputs:

- `data/processed_discovery_ablation/`
- `data/processed_flusurvnet_multiseason/recommended_completed_seasons.csv`

## Compact Derived Artifacts Included

The package includes compact CSV/JSON/Markdown summaries:

- `artifacts_discovery_ablation/`
- `artifacts_multiseason_robustness_compact/`
- `artifacts_selection_policy_eval_compact/`

These compact artifacts support the frozen paper narrative. They intentionally omit old exploratory artifact roots, per-model diagnostic PNG dumps, and heavy intermediate traces.

## Regeneration Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Rebuild the baseline/discovery comparison report from frozen artifacts:

```bash
python scripts/build_baseline_comparison_report.py --artifact-root artifacts_discovery_ablation --reference constrained_structure_discovery
```

Rebuild paper figures from compact CSV artifacts:

```bash
python scripts/build_paper_figures.py
```

Rebuild the multi-season robustness appendix report:

```bash
python scripts/build_multiseason_robustness_report.py --artifact-root artifacts_multiseason_robustness_compact
```

Rebuild the offline selection-policy report:

```bash
python scripts/build_selection_policy_report.py --artifact-root artifacts_selection_policy_eval_compact
```

Rebuild the optional API proposal smoke report from existing compact outputs:

```bash
python scripts/build_api_proposal_report.py --artifact-root artifacts_selection_policy_eval_compact
```

Rebuild the synthetic structured recovery report:

```bash
python scripts/build_selection_synthetic_recovery_report.py --artifact-root artifacts_selection_policy_eval_compact
```

The commands above rebuild reports and figures from included compact artifacts. They do not require rerunning the full frozen benchmark. The full frozen benchmark can be rerun with `configs/discovery_ablation.yaml`, but that is a separate experiment-level operation and is not needed for final paper packaging.

## Claim Boundaries

The included artifacts support a retrospective, age- and objective-dependent FluSurv-NET case study. They do not support a FluSight leaderboard claim, a state-of-the-art forecasting claim, an autonomous scientific-discovery claim, or a real-world mechanism-recovery claim. API-assisted proposal outputs are proposal-quality evidence only. Synthetic structured recovery outputs are generic software validation only.
