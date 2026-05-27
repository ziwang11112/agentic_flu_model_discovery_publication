# Publication Package

This repository is the clean publication package for the constrained influenza model-discovery project.

The full research/archive repository is:
`ziwang11112/agentic_flu_model_discovery`

This clean repository preserves:
- source code required for the frozen benchmark pipeline
- opt-in forecasting baselines
- discovery ablations
- paired rolling-origin comparison
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

## Main reproduction commands

```bash
pip install -r requirements.txt
python run_experiment.py --config configs/discovery_ablation.yaml --log-level INFO
python scripts/build_baseline_comparison_report.py --artifact-root artifacts_discovery_ablation --reference constrained_structure_discovery
python scripts/build_paper_figures.py
```

## Paper figures

Figures are generated from compact frozen CSV artifacts:

```bash
python scripts/build_paper_figures.py
```
