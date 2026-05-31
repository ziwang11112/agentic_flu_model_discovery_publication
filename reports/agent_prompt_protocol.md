# Constrained Agent Prompt Protocol

This protocol defines the structured proposer used by the verifier-gated selection framework. It is a prompt/task contract, not an autonomous scientific agent. The proposer receives a task context, an explicit candidate allowlist, non-final evidence summaries, and optional verifier/evaluator feedback. It returns JSON candidate records that are parsed, allowlist-checked, and verifier-checked before any replay or deterministic execution.

The proposer must not generate model code, arbitrary equations, intervention guidance, operational recommendations, or unrestricted model families. It must not receive held-out final-split metrics, final winners/ranks, or post-selection comparisons. Those quantities may appear only outside the prompt as post-hoc descriptive fields after selection.

## Shared Allowlist

Candidates are restricted to known families and model names, for example:

```json
{
  "families": ["forecasting_baseline", "mechanistic_baseline", "structured_search", "ablation"],
  "model_names": [
    "last_observed",
    "rolling_mean_4wk",
    "arima_auto_small",
    "deterministic_seir",
    "delayed_observation_seir",
    "constrained_structure_discovery",
    "no_observation_search_discovery",
    "validation_only_structure_selection",
    "random_structure_discovery",
    "exhaustive_structure_discovery"
  ],
  "observation_labels": ["direct", "lagged", "mixture", "proxy", "not_applicable"],
  "delay_labels": ["0", "1", "2", "not_applicable"]
}
```

## Task A: Initial Candidate Proposal

Purpose: propose a compact, diverse allowlisted candidate set for the first evaluation round.

Allowed context includes series name, forecasting target, partial-observation note, candidate budget, candidate allowlist, available non-final validation or rolling summaries, numerical-risk indicators, candidate family metadata, and family/observation labels already tried.

Forbidden context fields include held-out final-split metric names such as `test_mae`, final winner/rank fields such as `test_winner` or `test_rank`, and post-selection comparison fields such as `post_selection_test_mae`.

Required output fields: `task_type`, `series_name`, `round_index`, `proposer_label`, `candidates`, and `selection_notes`. Each candidate must include `candidate_id`, `family`, `model_name`, `observation_label`, and `delay_label`.

Verifier expectations:
- candidate ids are unique;
- family and model name are compatible with the allowlist;
- observation and delay labels are allowlisted;
- executable-code fields are absent;
- the claim boundary remains proposal-only.

## Task B: Evidence-Aware Refinement

Purpose: use prior verifier and non-final evaluator feedback to propose the next candidate round.

Allowed context includes accepted candidates, rejected candidates and rejection reasons, duplicate candidates, remaining budget, non-final rolling or validation summaries, numerical-risk notes, and missing family/observation-label coverage.

Required output fields: `task_type`, `series_name`, `round_index`, `new_candidates`, and `refinement_summary`. New candidates follow the same candidate schema as Task A and should state which feedback category they address.

Verifier expectations:
- invalid rejected candidates are not repeated;
- candidate ids do not duplicate prior accepted ids;
- feedback categories are drawn from the allowed context;
- no held-out final evidence is referenced.

## Task C: Failure Diagnosis / Ablation Request

Purpose: convert non-final failure evidence into a structured ablation request. This task does not execute the ablation.

Allowed context includes the candidate that failed, non-final failure type, numerical-risk flag, whether observation-label uncertainty is plausible, and the allowed ablation model list.

Required output fields: `task_type`, `series_name`, `diagnosis`, `recommended_ablation`, `reason`, and `claim_boundary`.

Verifier expectations:
- recommended ablation is in the allowed ablation list;
- diagnosis does not claim real-world mechanism recovery;
- `claim_boundary` is `ablation_request_only`.

## Task D: Claim-Boundary Summary

Purpose: summarize deterministic audit labels without expanding the allowed claim boundary. The deterministic auditor remains authoritative; this task can only produce a human-readable constrained summary.

Allowed context includes audit labels, allowed claim categories, rejected claim categories, and required caveats.

Required output fields: `task_type`, `safe_summary`, `allowed_claims`, `rejected_claims`, and `required_caveats`.

Verifier expectations:
- the summary treats API output as proposal-quality evidence only;
- synthetic tasks are described as generic structured time-series software validation;
- frozen real-data replay and bounded execution support budget-efficiency evidence only;
- flagged rows are descriptive only;
- global superiority, autonomous-science, and real-world mechanism-recovery claims are rejected.

## No-Leakage Audit Fields

Every generated prompt or replay context is auditable with:

- `prompt_contains_test_metric`
- `prompt_contains_test_winner`
- `prompt_contains_posthoc_metric`
- `safe_prompt_passed`
- `allowlist_hash`

Prompt construction rejects contexts containing explicit forbidden held-out fields before the provider sees them.

## Example Valid Candidate Output

```json
{
  "task_type": "initial_candidate_proposal",
  "series_name": "0-4 yr",
  "round_index": 1,
  "proposer_label": "constrained_agentic_proposer",
  "candidates": [
    {
      "candidate_id": "r1_c1",
      "family": "structured_search",
      "model_name": "constrained_structure_discovery",
      "observation_label": "lagged",
      "delay_label": "1",
      "intended_role": "observation_check",
      "rationale": "Tests whether a lagged observation label improves non-final rolling evidence.",
      "expected_failure_mode": "May overfit if lag evidence is unstable.",
      "paired_ablation_target": "no_observation_search_discovery"
    }
  ],
  "selection_notes": {
    "diversity_strategy": "Include a structured-search candidate and a paired observation-label ablation.",
    "budget_strategy": "Spend the small budget on observation uncertainty and simple comparators.",
    "claim_boundary": "proposal_only_not_performance_evidence"
  }
}
```
