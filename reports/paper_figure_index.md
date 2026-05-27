# Paper Figure Index

These figures are generated from frozen CSV artifacts under `artifacts_discovery_ablation/` by running:

```bash
python scripts/build_paper_figures.py
```

No new experiments are run, and frozen result CSVs are not modified.

## Figure 1: Age- and objective-aware model recommendations

Different age strata favor different model families and objectives; this supports objective-aware recommendation rather than a single global winner.

- PDF: `paper_draft/figures/fig1_recommendation_map.pdf`
- PNG: `paper_draft/figures/fig1_recommendation_map.png`

## Figure 2: Impact of observation-map search

Positive values favor observation-aware discovery. Pediatric strata show the clearest rolling-origin benefit from allowing delayed observation maps.

- PDF: `paper_draft/figures/fig2_observation_search_impact.pdf`
- PNG: `paper_draft/figures/fig2_observation_search_impact.png`

## Figure 3: Discovery ablations across age strata

Rolling-origin MAE is ranked within each age stratum across same-grammar discovery variants; darker cells indicate better within-stratum ranks.

- PDF: `paper_draft/figures/fig3_discovery_ablation_matrix.pdf`
- PNG: `paper_draft/figures/fig3_discovery_ablation_matrix.png`

## Figure 4: Paired rolling-origin comparisons against constrained discovery

Mean paired rolling absolute-error differences are challenger minus constrained discovery; positive values mean constrained discovery has lower rolling error.

- PDF: `paper_draft/figures/fig4_paired_rolling_forest.pdf`
- PNG: `paper_draft/figures/fig4_paired_rolling_forest.png`

## Figure 5: Numerical failure flags by model family

Flagged rows are retained for transparency but not used to support positive claims.

- PDF: `paper_draft/figures/fig5_numerical_failure_audit.pdf`
- PNG: `paper_draft/figures/fig5_numerical_failure_audit.png`
