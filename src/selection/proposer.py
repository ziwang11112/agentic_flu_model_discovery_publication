from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.selection.schema import CandidateSpec
from src.selection.verifier import infer_family


@dataclass(frozen=True)
class SeedCandidateProposer:
    """Deterministically emit candidates represented in compact summary tables."""

    name: str = "seed_candidate_proposer"

    def propose(self, model_summary: pd.DataFrame, max_candidates: int | None = None) -> list[CandidateSpec]:
        candidates: list[CandidateSpec] = []
        columns = set(model_summary.columns)
        grouped = model_summary.sort_values(["model_name", "series_name"]).groupby("model_name", sort=True)
        for model_name, subset in grouped:
            first = subset.iloc[0]
            try:
                family = infer_family(str(model_name))
            except ValueError:
                continue
            observation_label = None
            delay_label = None
            if "discovery_observation_map" in columns and pd.notna(first.get("discovery_observation_map")):
                observation_label = str(first["discovery_observation_map"])
            if "discovery_delay_weeks" in columns and pd.notna(first.get("discovery_delay_weeks")):
                delay_label = str(first["discovery_delay_weeks"])
            candidates.append(
                CandidateSpec(
                    candidate_id=f"seed:{model_name}",
                    family=family,
                    model_name=str(model_name),
                    observation_label=observation_label,
                    delay_label=delay_label,
                    proposer_name=self.name,
                    rationale="present in frozen compact summary",
                    expected_failure_mode="from_frozen_diagnostics",
                    metadata={"source_table": "benchmark_model_summary.csv"},
                )
            )
            if max_candidates is not None and len(candidates) >= max_candidates:
                break
        return candidates


@dataclass(frozen=True)
class FailureGuidedRefinementProposer:
    """Emit deterministic safety/refinement candidates from compact diagnostics."""

    name: str = "failure_guided_refinement_proposer"

    def propose(
        self,
        *,
        numerical_summary: pd.DataFrame | None = None,
        observation_impact: pd.DataFrame | None = None,
        max_candidates: int | None = None,
    ) -> list[CandidateSpec]:
        candidates: list[CandidateSpec] = []
        if numerical_summary is not None and not numerical_summary.empty:
            flagged = numerical_summary.loc[numerical_summary["numerical_failure_flag"].astype(bool)].copy()
            for model_name in sorted(flagged["model_name"].astype(str).unique()):
                candidates.append(
                    CandidateSpec(
                        candidate_id=f"refinement:simpler_after_failure:{model_name}",
                        family="forecasting_baseline",
                        model_name="rolling_mean_4wk",
                        proposer_name=self.name,
                        rationale=f"simpler fallback after numerical flag in {model_name}",
                        expected_failure_mode="numerical_instability",
                        metadata={"flagged_model": model_name},
                    )
                )
                if max_candidates is not None and len(candidates) >= max_candidates:
                    return candidates

        if observation_impact is not None and not observation_impact.empty:
            for series_name in sorted(observation_impact["series_name"].astype(str).unique()):
                candidates.append(
                    CandidateSpec(
                        candidate_id=f"refinement:observation_ablation:{series_name}",
                        family="ablation",
                        model_name="no_observation_search_discovery",
                        observation_label="I",
                        proposer_name=self.name,
                        rationale="compare observation label search against fixed-label ablation",
                        expected_failure_mode="observation_label_not_needed",
                        metadata={"series_name": series_name},
                    )
                )
                if max_candidates is not None and len(candidates) >= max_candidates:
                    return candidates
        return candidates
