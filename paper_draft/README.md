# Paper Draft

This directory contains the LaTeX paper draft for the frozen
discovery-ablation publication package.

Current sections:

- `sections/introduction.tex`
- `sections/method.tex`
- `sections/experiments.tex`
- `sections/results.tex`
- `sections/limitations.tex`

Main entry point:

- `main.tex`

Frozen result provenance:

- main config: `configs/discovery_ablation.yaml`
- artifact root: `artifacts_discovery_ablation`
- main report: `reports/baseline_ablation_report.md`
- result artifact commit: `09c93188e319aa51933f6029260fff2f3a09cd03`
- paper integration commit: `3608b641dc45ab35a347059ef53567371ce62f1e`

Generated paper figures live under `figures/`. They can be rebuilt from frozen
CSV artifacts with:

```bash
python ../scripts/build_paper_figures.py
```

The figure index is `../reports/paper_figure_index.md`.

If `latexmk` is available, compile from this directory with:

```bash
latexmk -pdf main.tex
```
