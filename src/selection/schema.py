from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class CandidateFamily(str, Enum):
    """Model-family labels used by the offline selection layer."""

    FORECASTING_BASELINE = "forecasting_baseline"
    MECHANISTIC_BASELINE = "mechanistic_baseline"
    STRUCTURED_SEARCH = "structured_search"
    ABLATION = "ablation"
    ENSEMBLE = "ensemble"


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    family: CandidateFamily | str
    model_name: str
    observation_label: str | None = None
    delay_label: str | None = None
    round_idx: int = 0
    proposer_name: str = "deterministic"
    rationale: str = ""
    expected_failure_mode: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized_family(self) -> CandidateFamily:
        return self.family if isinstance(self.family, CandidateFamily) else CandidateFamily(str(self.family))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["family"] = self.normalized_family().value
        return data


@dataclass(frozen=True)
class VerificationResult:
    candidate_id: str
    valid: bool
    vetoed: bool
    reasons: tuple[str, ...] = ()
    schema_valid: bool = True
    family_valid: bool = True
    leakage_safe: bool = True
    budget_safe: bool = True
    artifact_safe: bool = True
    claim_safe: bool = True
    duplicate: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        return data


@dataclass(frozen=True)
class EvidencePacket:
    candidate_id: str
    model_name: str
    family: CandidateFamily | str
    series_name: str
    selection_metrics: dict[str, float | None] = field(default_factory=dict)
    posthoc_metrics: dict[str, float | None] = field(default_factory=dict)
    rolling_mean_mae: float | None = None
    num_free_params: float | None = None
    numerical_failure_flag: bool = False
    supports_positive_claim: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized_family(self) -> CandidateFamily:
        return self.family if isinstance(self.family, CandidateFamily) else CandidateFamily(str(self.family))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["family"] = self.normalized_family().value
        return data


@dataclass(frozen=True)
class PolicyDecision:
    policy_name: str
    selected_candidate_id: str | None
    selected_model_name: str | None
    selected_ids: tuple[str, ...] = ()
    rationale: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["selected_ids"] = list(self.selected_ids)
        return data


@dataclass(frozen=True)
class ClaimBoundaryAudit:
    no_single_global_winner: bool
    age_or_group_specific_signal: bool
    simple_baseline_competitive: bool
    flagged_rows_descriptive_only: bool
    posthoc_comparison_not_selection: bool
    multiseason_mixed_if_present: bool | None
    allowed_claims: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    rejected_claims: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["allowed_claims"] = list(self.allowed_claims)
        data["caveats"] = list(self.caveats)
        data["rejected_claims"] = list(self.rejected_claims)
        return data


@dataclass(frozen=True)
class TraceEvent:
    event_type: str
    candidate_id: str | None = None
    round_idx: int = 0
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BudgetState:
    max_candidates: int
    evaluated_candidates: int = 0
    round_idx: int = 0

    @property
    def remaining(self) -> int:
        return max(0, int(self.max_candidates) - int(self.evaluated_candidates))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
