# Reference Matrix

This matrix maps the paper's core references to the claim boundary they support. The references are used for framing and attribution, not to claim FluSight leaderboard performance, state-of-the-art forecasting, autonomous scientific discovery, or real-world mechanism recovery.

| Area | BibTeX keys | Role in the paper | Boundary |
| --- | --- | --- | --- |
| LLM/evaluator scientific discovery | `romera2024funsearch`, `shojaee2024llmsr`, `lu2024aiscientist` | Motivates proposal-and-evaluation loops and evaluator-guided search. | This work does not claim fully autonomous science. API-assisted proposal is optional, allowlisted, and verifier-checked. |
| Symbolic and equation discovery | `brunton2016sindy`, `udrescu2020aifeynman`, `cranmer2023pysr` | Provides context for interpretable equation discovery from data. | The structured search here is narrower and bounded by a fixed candidate grammar; it is not an unconstrained symbolic-regression comparison. |
| Influenza forecasting, FluSight, and Flusion | `reich2019collaborative`, `reich2019accuracy`, `lutz2019pathforward`, `ray2024flusion` | Places the FluSurv-NET case study near operational influenza forecasting work. | The frozen benchmark is retrospective and is not a FluSight leaderboard claim or a Flusion comparison. |
| Mechanistic influenza forecasting | `shaman2012forecasting`, `shaman2013realtime` | Supports the use of mechanistic state-space structure in seasonal influenza forecasting. | The paper compares hand-specified mechanistic baselines with forecasting baselines and structured search; it does not claim true mechanism discovery. |
| Forecast evaluation and rolling-origin design | `tashman2000outofsample`, `hyndman2021fpp3` | Supports held-out and rolling-origin evaluation choices. | Test metrics are post-selection evidence. Rolling-origin comparisons are post-hoc reporting, not model selection. |
| CDC FluSurv-NET and RESP-NET data sources | `cdcFluSurvNet2026`, `cdcRespNet2026`, `naquin2024flusurvnet` | Attributes hospitalization-surveillance data and the FluSurv-NET source. | Users should verify CDC/RESP-NET source terms before public redistribution of derivative packages. |
| Multi-objective and Pareto selection | `deb2002nsga2` | Provides background for Pareto-style multi-objective model selection. | `pareto_epsilon` is an offline deterministic policy, not a claim that Pareto selection is universally best. |
