# Final Manuscript Package

This folder is a self-contained manuscript bundle for the verifier-gated
cross-family model-selection paper.

## Compile

The LaTeX entry point is:

```bash
main.tex
```

The manuscript expects the following local paths:

- `sections/`
- `figures/`
- `references.bib`

If a local TeX distribution is available, compile from this folder with:

```bash
latexmk -pdf main.tex
```

The repository-level GitHub Actions workflow copied under
`metadata/github_workflow/build-paper.yml` can also compile the paper from the
original repository layout.

## Included

- `main.tex`
- `references.bib`
- `sections/*.tex`
- all manuscript figures under `figures/`
- compact experiment reports under `reports/`
- compact CSV/JSON/Markdown result summaries under `artifacts/`
- data/package metadata under `metadata/`

## Not Included

The package intentionally excludes:

- API keys or local `.env` files
- local API configs
- temporary execution directories
- raw forecast traces
- JSONL trace files
- logs
- NumPy/pickle binaries
- raw per-model diagnostic outputs

The included artifacts support claim-bounded manuscript evidence only. They do
not support forecasting state-of-the-art claims, autonomous-science claims,
medical or operational recommendations, provider clinical superiority claims,
or real-world mechanism-recovery claims.
