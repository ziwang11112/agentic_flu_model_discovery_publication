# Related Work Reference Matrix

This matrix keeps the bibliography focused for *Verifier-Gated Agentic Model Selection under Partial Observation*. It is intentionally not a survey dump. Drug-discovery references are used only as cross-domain analogies for proposal-filter-evaluate-feedback and claim discipline.

| Citation key | Bucket | Why included | Claim supported | Claim boundary | Where cited |
|---|---|---|---|---|---|
| `anderson1991infectious` | Mechanistic epidemic forecasting | Canonical compartmental epidemic-model reference. | Mechanistic baselines use interpretable latent-state templates. | Does not validate our fitted structures or forecasting performance. | Related Work A |
| `keeling2008modeling` | Mechanistic epidemic forecasting | Standard epidemic modeling text. | Compartmental templates provide constrained dynamics. | Not evidence for real-world mechanism recovery. | Related Work A |
| `breto2009mechanistic` | Mechanistic epidemic forecasting | Mechanistic time-series inference framing. | Epidemic time-series models require latent dynamics plus observation assumptions. | Does not support unrestricted discovery claims. | Related Work A |
| `king2016pomp` | Mechanistic / partial observation | POMP framework for partially observed mechanistic systems. | Observation models must be separated from latent dynamics. | Not a claim that our models are epidemiologically causal. | Related Work A/B |
| `shaman2012forecasting` | Operational influenza forecasting | Early seasonal influenza forecasting example. | Influenza forecasting has a strong operational tradition. | Not a FluSight leaderboard comparison. | Related Work A |
| `shaman2013realtime` | Operational influenza forecasting | Real-time influenza forecast evaluation. | Real-time influenza forecasting motivates careful evaluation. | Not evidence of operational readiness. | Related Work A |
| `biggerstaff2016challenge` | Operational influenza / FluSight | CDC influenza season challenge. | FluSight-style challenges established comparative forecast assessment. | Not used to claim FluSight performance. | Related Work A |
| `mcgowan2019collaborative` | Operational influenza forecasting | Collaborative influenza forecasting overview. | Multi-model assessment is standard in flu forecasting. | Not a direct benchmark baseline here. | Related Work A |
| `reich2019collaborative` | Operational influenza forecasting | Multi-year multimodel influenza assessment. | Cross-model disagreement matters for credible recommendations. | Not a leaderboard claim. | Related Work A |
| `reich2019accuracy` | Operational influenza forecasting | Real-time ensemble forecast accuracy. | Ensemble and multimodel evaluation motivate cross-family comparison. | Not state-of-the-art evidence. | Related Work A |
| `lutz2019pathforward` | Operational influenza forecasting | Public-health forecasting path-forward paper. | Separates forecasting systems from public-health use. | We make no operational recommendations. | Related Work A |
| `ray2025flusion` | Operational influenza / Flusion | Recent multi-source influenza prediction system. | Operational flu systems differ from this retrospective case study. | Not a Flusion or FluSight replacement. | Related Work A |
| `cdcFluSurvNet2026` | Data source | CDC FluSurv-NET source attribution. | Identifies the real-data case-study source. | Users must verify redistribution terms. | Data availability / references |
| `cdcRespNet2026` | Data source | CDC RESP-NET source attribution. | Identifies multi-season raw-data source. | Not a derived-data redistribution license. | Data availability / references |
| `naquin2024flusurvnet` | FluSurv-NET context | Published FluSurv-NET hospitalization summary. | Context for FluSurv-NET surveillance data. | Not a validation of our recommendations. | Data/case-study context |
| `lawless1994reporting` | Partial observation / delay | Reporting-delay analysis reference. | Delays and reporting processes affect observed time series. | Not an intervention or operational correction. | Related Work B |
| `mcgough2020nowcasting` | Partial observation / nowcasting | Nowcasting reporting-delay framework. | Observation timing must be modeled separately from final outcomes. | Not a claim that our delay labels recover true reporting processes. | Related Work B |
| `tashman2000outofsample` | Forecast evaluation | Out-of-sample forecast evaluation review. | Selection and evaluation require separated evidence. | Not sufficient alone for no-leakage guarantees. | Related Work B |
| `hyndman2021fpp3` | Forecast evaluation | Forecasting textbook with rolling-origin/backtesting concepts. | Rolling-origin evaluation is appropriate for time series. | Not a specific benchmark result. | Related Work B |
| `bergmeir2012cv` | Forecast evaluation | Cross-validation for time-series prediction. | Time-series validation needs temporal care. | Not a license to use random folds. | Related Work B |
| `roberts2017cv` | Forecast evaluation / leakage | Cross-validation under structured dependence. | Structured dependence can make naive validation misleading. | Not a biological claim. | Related Work B |
| `kaufman2012leakage` | No-leakage evaluation | Leakage in data-mining evaluation. | Leakage can inflate model-selection evidence. | Does not diagnose all possible leakage in our code by itself. | Related Work B |
| `kapoor2023leakage` | No-leakage evaluation | Leakage and reproducibility in ML science. | Held-out test metrics must be excluded from selection prompts. | Not a result artifact. | Related Work B |
| `schmidt2009distilling` | Symbolic regression | Classic symbolic regression/equation discovery. | Equation-discovery systems search interpretable structures. | Our framework is not unrestricted equation discovery. | Related Work C |
| `brunton2016sindy` | Symbolic regression | SINDy reference. | Sparse equation discovery motivates structured search comparisons. | Not a direct SINDy benchmark. | Related Work C |
| `udrescu2020aifeynman` | Symbolic regression | AI Feynman equation discovery. | Physics-inspired symbolic discovery contextualizes model search. | Not evidence for epidemic mechanism recovery. | Related Work C |
| `cranmer2023pysr` | Symbolic regression | PySR / SymbolicRegression.jl. | Modern symbolic regression contextualizes interpretable search. | Not included as a baseline experiment. | Related Work C |
| `lacava2021symbolic` | Symbolic regression | SRBench benchmark. | Benchmarks are needed to compare symbolic regression methods. | Not a claim that our grammar matches SRBench. | Related Work C |
| `romera2024funsearch` | LLM/evaluator loops | FunSearch proposal/evaluation loop. | LLM-backed proposal can be useful when evaluator/guardrails are explicit. | Not a claim of autonomous science. | Related Work C |
| `shojaee2024llmsr` | LLM/evaluator loops | LLM-SR equation-discovery loop. | LLMs can propose candidates for external evaluation. | Our LLM-backed proposer cannot invent equations. | Related Work C |
| `lu2024aiscientist` | LLM scientific discovery | AI Scientist motivates autonomous-science contrast. | Helps position our work as constrained, not fully autonomous. | We reject autonomous-scientist claims. | Related Work C |
| `yao2023react` | Agentic proposal | ReAct reasoning/action loop. | Agentic systems can use stateful reasoning and feedback. | Our tools are deterministic and verifier-gated. | Related Work D |
| `madaan2023selfrefine` | Agentic proposal | Self-refinement feedback loop. | Iterative proposer feedback can improve candidate records. | Not proof that iterative feedback is always superior. | Related Work D |
| `liu2023agentbench` | Agent benchmarks | Agent behavior benchmark. | Agentic protocols should be evaluated, not assumed. | Not a provider superiority claim. | Related Work D |
| `snoek2012bayesian` | Budgeted model selection / AutoML | Bayesian optimization for model selection. | Candidate-budget allocation is an established concern. | We do not implement full Bayesian optimization. | Related Work D |
| `feurer2015automl` | AutoML | Efficient robust AutoML reference. | Automated model selection motivates fixed-budget comparison. | Not an AutoML leaderboard claim. | Related Work D |
| `li2018hyperband` | Budgeted model selection | Hyperband adaptive resource allocation. | Budget-to-good-candidate metrics are meaningful. | Not used as a competing method here. | Related Work D |
| `deb2002nsga2` | Pareto multi-objective selection | NSGA-II / Pareto optimization. | Multi-objective model selection motivates Pareto-epsilon policy. | Does not imply Pareto is universally best. | Related Work D |
| `loeffler2024reinvent` | Cross-domain claim discipline | ARISE A_full_text; constrained generative molecule-design workflow. | Cross-domain analogy for proposal-filter-feedback separation. | Does not support influenza, clinical, or mechanism claims. | Related Work E |
| `liu2023drugex` | Cross-domain claim discipline | ARISE A_full_text; scaffold-constrained generative design. | Cross-domain analogy for constrained candidate proposal. | Not evidence for epidemic forecasting. | Related Work E |
| `thomas2024molscore` | Cross-domain claim discipline | ARISE A_full_text; scoring and benchmarking generative designs. | Cross-domain analogy for evaluator-first discipline. | Not evidence for provider superiority or clinical use. | Related Work E |
| `arvidsson2024cpsign` | Cross-domain claim discipline | ARISE A_full_text; conformal prediction in cheminformatics. | Cross-domain analogy for calibrated/claim-bounded evidence. | Not evidence for FluSurv-NET recommendations. | Related Work E |
## Survey Policy Check

- Drug-discovery references included: 4.
- Preferred ARISE evidence level: all four selected drug-discovery references are A_full_text entries in `supplementary_evidence_status.csv`.
- Excluded survey-style references: broad C/D-preview drug-discovery items and references used only to imply biomedical or clinical performance.
- Boundary: these references support only proposal/evaluator separation, feedback, benchmarking, calibration, and claim discipline.
