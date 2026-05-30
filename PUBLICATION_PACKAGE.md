# Publication Package

This repository is the clean publication package for the constrained influenza model-discovery project.

The full research/archive repository is:
`ziwang11112/agentic_flu_model_discovery`

This clean repository preserves:
- source code required for the frozen benchmark pipeline
- opt-in forecasting baselines
- discovery ablations
- paired rolling-origin comparison
- compact multi-season robustness appendix
- paper draft and figures
- compact frozen result CSVs
- freeze and interpretation reports

It intentionally omits:
- old exploratory artifacts
- LLM traces and prompts
- smoke outputs
- old multiseed/age-robustness/conformal artifact roots
- per-model diagnostic PNGs and heavy traces not needed by the paper figures

## Frozen result provenance

See:
- `reports/result_freeze_manifest.md`
- `reports/discovery_ablation_interpretation.md`
- `reports/numerical_failure_audit.md`
- `reports/reference_matrix.md`
- `DATA_AVAILABILITY.md`

## Main reproduction commands

```bash
pip install -r requirements.txt
python run_experiment.py --config configs/discovery_ablation.yaml --log-level INFO
python scripts/build_baseline_comparison_report.py --artifact-root artifacts_discovery_ablation --reference constrained_structure_discovery
python scripts/build_paper_figures.py
python scripts/run_multiseason_robustness.py --config configs/multiseason_robustness.yaml --log-level INFO
python scripts/build_multiseason_robustness_report.py --artifact-root artifacts_multiseason_robustness_compact
```

## Data attribution

The multi-season appendix uses CDC RESP-NET dataset `kvib-3txy`, transformed to
FluSurv-NET hospitalization rates. Completed seasons are used for appendix
robustness checks; incomplete `2020-21` and preliminary `2025-26` are excluded
from paper-level claims. Users should cite CDC/RESP-NET and verify
redistribution terms before making derivative packages public. See
`DATA_AVAILABILITY.md` for the included raw files, compact derived artifacts,
and regeneration commands.

## Paper figures

Figures are generated from compact frozen CSV artifacts:

```bash
python scripts/build_paper_figures.py
```
