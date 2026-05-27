from __future__ import annotations

import numpy as np

from src.models.base import BaseEpidemicModel, FitConfig, SimulationResult
from src.models.simulators import euler_discrete_simulation
from src.utils.math_utils import seasonal_beta, sigmoid, softmax


def _logit(probability: float) -> float:
    probability = min(max(probability, 1.0e-6), 1.0 - 1.0e-6)
    return float(np.log(probability / (1.0 - probability)))


class DeterministicSEIRModel(BaseEpidemicModel):
    """Manual deterministic SEIR baseline."""

    def __init__(self, fit_config: FitConfig) -> None:
        super().__init__(fit_config)

    @property
    def model_name(self) -> str:
        return "deterministic_seir"

    @property
    def compartment_names(self) -> tuple[str, ...]:
        return ("S", "E", "I", "R")

    @property
    def raw_parameter_dim(self) -> int:
        return 8

    def sample_initial_parameters(self, y_train: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        rho_guess = np.log(max(float(np.max(y_train)) / 0.01, 1.0))
        center = np.array(
            [
                -2.0,
                0.15,
                -0.15,
                _logit(0.25),
                _logit(0.35),
                rho_guess,
                -4.0,
                -5.0,
            ],
            dtype=float,
        )
        return center + rng.normal(loc=0.0, scale=0.7, size=center.size)

    def transform_parameters(self, raw_params: np.ndarray) -> dict[str, float]:
        init_simplex = softmax(np.array([0.0, raw_params[6], raw_params[7]], dtype=float))
        sigma = float(sigmoid(raw_params[3]))
        gamma = float(sigmoid(raw_params[4]))
        rho = float(np.exp(np.clip(raw_params[5], -12.0, 14.0)))
        return {
            "b0": float(raw_params[0]),
            "b1": float(raw_params[1]),
            "b2": float(raw_params[2]),
            "sigma": sigma,
            "gamma": gamma,
            "rho": rho,
            "S0": float(init_simplex[0]),
            "E0": float(init_simplex[1]),
            "I0": float(init_simplex[2]),
            "R0": 0.0,
        }

    def simulate(self, raw_params: np.ndarray, n_steps: int) -> SimulationResult:
        params = self.transform_parameters(raw_params)
        initial_state = np.array([params["S0"], params["E0"], params["I0"], params["R0"]], dtype=float)

        def drift_fn(state: np.ndarray, t: int) -> np.ndarray:
            beta_t = float(seasonal_beta(t, params["b0"], params["b1"], params["b2"]))
            s_val, e_val, i_val, _ = state
            infection = beta_t * s_val * i_val
            return np.array(
                [
                    -infection,
                    infection - params["sigma"] * e_val,
                    params["sigma"] * e_val - params["gamma"] * i_val,
                    params["gamma"] * i_val,
                ],
                dtype=float,
            )

        states = euler_discrete_simulation(initial_state, n_steps, drift_fn)
        predictions = params["rho"] * states[:, 2]
        return SimulationResult(
            compartments=self.compartment_names,
            states=states,
            predictions=predictions,
            penalties=self.penalty_summary(states),
        )
