# API-Assisted Structured Proposal Evaluation

This report summarizes an optional API-assisted structured candidate proposal check.
The API layer is disabled or skipped when credentials are absent. API output is accepted only as JSON,
restricted to an explicit allowlist, and passed through the same verifier before any use.
It cannot create model code and does not run new forecasting experiments.

## Status

- Status: `skipped`.
- External API used: `False`.
- Skip reason: `api_disabled`.

## Metrics

| api_run_status | proposal_count | valid_proposal_count | valid_proposal_rate | duplicate_rate | family_diversity | observation_label_diversity | top_epsilon_useful_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| skipped | 0 | 0 | 0.0000 | 0.0000 | 0 | 0 | 0.0000 |

## Verified Candidate Records

_None._

## Caveats

- This is proposal-quality evaluation over frozen compact summaries, not a model performance experiment.
- Tests use deterministic mock responses and do not require API credentials.
- Any real API output is constrained by JSON parsing, allowlists, and verifier checks.
