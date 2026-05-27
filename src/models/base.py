from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import minimize

from src.models.simulators import mass_conservation_penalty, negative_state_penalty


@dataclass
class FitConfig:
    """Shared optimization settings."""

    n_restarts: int = 12
    rolling_n_restarts: int = 2
    maxiter: int = 400
    negative_penalty: float = 1.0e4
    mass_penalty: float = 1.0e4
    prior_weight: float = 1.0e-3
    laplace_draws: int = 250
    uncertainty_method: str = "laplace"
    bootstrap_draws: int = 40
    bootstrap_n_restarts: int = 0
    calibrate_intervals: bool = True
    interval_calibration_method: str = "conformal"
    calibration_draws: int = 12
    calibration_scale_min: float = 0.25
    calibration_scale_max: float = 1.25
    calibration_scale_grid_size: int = 41
    seed: int = 42


@dataclass
class SimulationResult:
    """Model rollout and constraint summaries."""

    compartments: tuple[str, ...]
    states: np.ndarray
    predictions: np.ndarray
    penalties: dict[str, float]


@dataclass
class FitResult:
    """Optimization outcome for one model family."""

    model_name: str
    raw_params: np.ndarray
    params: dict[str, float]
    simulation: SimulationResult
    objective: float
    success: bool
    message: str
    param_count: int
    extra: dict[str, Any] = field(default_factory=dict)


class BaseEpidemicModel(ABC):
    """Common fitting loop for compartmental benchmark models."""

    def __init__(self, fit_config: FitConfig) -> None:
        self.fit_config = fit_config

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Display name for the model."""

    @property
    @abstractmethod
    def compartment_names(self) -> tuple[str, ...]:
        """Compartment labels used by the model."""

    @property
    @abstractmethod
    def raw_parameter_dim(self) -> int:
        """Number of optimized parameters in unconstrained space."""

    @abstractmethod
    def sample_initial_parameters(self, y_train: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Draw one restart initialization."""

    @abstractmethod
    def transform_parameters(self, raw_params: np.ndarray) -> dict[str, float]:
        """Map unconstrained parameters to constrained model parameters."""

    @abstractmethod
    def simulate(self, raw_params: np.ndarray, n_steps: int) -> SimulationResult:
        """Forward-simulate the model."""

    def loss(self, y_true: np.ndarray, predictions: np.ndarray, raw_params: np.ndarray) -> float:
        """Default point-estimation objective."""
        return float(np.mean(np.square(y_true - predictions)))

    def objective(self, raw_params: np.ndarray, y_train: np.ndarray) -> float:
        with np.errstate(all="ignore"):
            simulation = self.simulate(raw_params, len(y_train))
            if not np.all(np.isfinite(simulation.states)) or not np.all(np.isfinite(simulation.predictions)):
                return 1.0e12

            penalties = (
                self.fit_config.negative_penalty * simulation.penalties["negative"]
                + self.fit_config.mass_penalty * simulation.penalties["mass"]
            )
            total_loss = self.loss(y_train, simulation.predictions, raw_params) + penalties

        if not np.isfinite(total_loss):
            return 1.0e12
        return float(total_loss)

    def fit(
        self,
        y_train: np.ndarray,
        rng: np.random.Generator,
        warm_start: np.ndarray | None = None,
        n_restarts: int | None = None,
    ) -> FitResult:
        """Fit the model with multiple random restarts."""
        total_restarts = self.fit_config.n_restarts if n_restarts is None else n_restarts
        if warm_start is None and total_restarts <= 0:
            total_restarts = 1
        candidates: list[np.ndarray] = []
        if warm_start is not None:
            candidates.append(np.asarray(warm_start, dtype=float))
        for _ in range(total_restarts):
            candidates.append(self.sample_initial_parameters(y_train, rng))

        best_result = None
        best_objective = float("inf")

        for initial_params in candidates:
            result = minimize(
                lambda raw: self.objective(raw, y_train),
                x0=initial_params,
                method="L-BFGS-B",
                options={"maxiter": self.fit_config.maxiter},
            )
            if result.fun < best_objective:
                best_objective = float(result.fun)
                best_result = result

        if best_result is None:
            raise RuntimeError(f"No optimization result for {self.model_name}")

        simulation = self.simulate(best_result.x, len(y_train))
        return FitResult(
            model_name=self.model_name,
            raw_params=np.asarray(best_result.x, dtype=float),
            params=self.transform_parameters(np.asarray(best_result.x, dtype=float)),
            simulation=simulation,
            objective=float(best_result.fun),
            success=bool(best_result.success),
            message=str(best_result.message),
            param_count=self.raw_parameter_dim,
        )

    def penalty_summary(self, states: np.ndarray) -> dict[str, float]:
        """Shared constraint summaries for rollouts."""
        return {
            "negative": negative_state_penalty(states),
            "mass": mass_conservation_penalty(states),
        }
