# Related Work Reference Integration

Scope: verifier-gated agentic model selection under partial observation.

This integration expands related work without changing experiments, artifacts, or result metrics. Drug-discovery survey references are used only as cross-domain evidence for proposal/evaluation loops, multi-objective evaluation, uncertainty/applicability-domain reporting, closed-loop feedback, and claim discipline. They are not used as evidence for influenza forecasting performance, FluSurv-NET conclusions, provider superiority, clinical recommendations, or epidemic mechanism recovery.

| Citation key | Bucket | Evidence tier | Claim supported | Claim boundary | Placement |
|---|---|---|---|---|---|
| `shaman2012forecasting` | A. Operational influenza forecasting | domain reference | Seasonal influenza forecasting context | Not a FluSight leaderboard claim for this paper | Main text |
| `shaman2013realtime` | A. Operational influenza forecasting | domain reference | Real-time influenza forecasting context | Not operational deployment evidence for this framework | Main text |
| `reich2019collaborative` | A. Operational influenza forecasting | domain reference | Collaborative multiyear influenza forecasting assessment | Not SOTA claim | Main text |
| `reich2019accuracy` | A. Operational influenza forecasting | domain reference | Multi-model ensemble accuracy context | Not a leaderboard claim | Main text |
| `lutz2019pathforward` | A. Operational influenza forecasting | domain reference | Public-health forecasting readiness context | Not deployment validation for this framework | Main text |
| `ray2024flusion` | A. Operational influenza forecasting | domain reference | Flusion/multisource influenza forecasting context | Not used to claim this paper improves FluSight | Main text |
| `brunton2016sindy` | C. Symbolic regression/equation discovery | strong external method reference | Interpretable equation discovery motivation | Our search is narrower and verifier-gated | Main text |
| `udrescu2020aifeynman` | C. Symbolic regression/equation discovery | strong external method reference | Equation discovery motivation | Not real-world mechanism recovery evidence | Main text |
| `cranmer2023pysr` | C. Symbolic regression/equation discovery | method reference | Symbolic regression tooling context | Not unconstrained discovery claim | Main text |
| `romera2024funsearch` | D. LLM/evaluator discovery loops | strong external method reference | Proposal/evaluation loop motivation | This paper restricts autonomy and execution | Main text |
| `shojaee2024llmsr` | D. LLM/evaluator discovery loops | method reference | LLM-guided scientific equation search context | Not autonomous science claim | Main text |
| `lu2024aiscientist` | D. LLM/evaluator discovery loops | method reference | AI-scientist framing to contrast against | This framework is not fully autonomous | Main text |
| `deb2002nsga2` | E. Multi-objective/Pareto selection | strong optimization reference | Pareto-style multi-objective selection | Not model-performance superiority evidence | Main text |
| `tashman2000outofsample` | F. No-leakage/out-of-sample evaluation | forecasting evaluation reference | Out-of-sample evaluation discipline | Does not validate FluSurv-NET claims alone | Main text |
| `hyndman2021fpp3` | F. Rolling-origin forecasting evaluation | forecasting text reference | Rolling-origin and forecasting evaluation practice | Does not imply operational readiness | Main text |
| `loeffler2024reinvent` | G. Cross-domain proposal/evaluation loop | A_full_text | Generative proposal must be paired with scoring/filtering | Drug-design example only; no flu-performance claim | Main text |
| `liu2023drugex` | G. Cross-domain constrained proposal/optimization | A_full_text | Scaffold-constrained proposal and objective-guided optimization | Cross-domain analogy only | Main text |
| `ai2024mtmolgpt` | G. Cross-domain multi-target proposal | A_full_text | Candidate generation under biological objectives | Not epidemic mechanism evidence | Main text |
| `lin2024diffbp` | G. Cross-domain conditioned generation | A_full_text | Proposal conditioned on target context requires downstream validation | Not flu mechanism evidence | Main text |
| `ivanenkov2023chemistry42` | G. Cross-domain platform proposal workflow | D_abstract in local survey supplement | Platform-style proposal/optimization orientation | Orientation only; not a strong technical anchor | Main text |
| `thomas2024molscore` | G. Cross-domain multi-objective evaluation | A_full_text | Benchmarking generated candidates under explicit objectives | Evaluation analogy only | Main text |
| `dutschmann2023uncertainty` | G. Cross-domain uncertainty evaluation | A_full_text | Uncertainty estimation as evaluation discipline | Not forecasting uncertainty validation here | Main text |
| `arvidsson2024cpsign` | G. Cross-domain conformal/applicability reporting | A_full_text | Applicability-domain and confidence-aware reporting | Analogy only; no clinical recommendation | Main text |
| `atz2024prospective` | G. Cross-domain closed-loop/prospective design | A_full_text | Candidate proposal gains credibility through prospective feedback | Not evidence for FluSurv-NET conclusions | Main text |
| `lavecchia2026mechanismaware` | G. Cross-domain mechanism-aware claim discipline | A_full_text | Mechanism-aware evaluation and claim discipline | Not real-world epidemic mechanism recovery | Main text |

Survey-related references integrated in main text: 10.

Preserved claim boundaries:

- no state-of-the-art forecasting claim;
- no FluSight leaderboard claim;
- no fully autonomous science claim;
- no real-world mechanism recovery claim;
- no provider clinical or forecasting superiority claim.
