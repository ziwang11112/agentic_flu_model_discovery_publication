from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import t as student_t

from src.models.base import BaseEpidemicModel, FitConfig, FitResult, SimulationResult
from src.models.simulators import euler_discrete_simulation
from src.utils.math_utils import finite_difference_hessian, seasonal_beta, sigmoid, softmax


def _logit(probability: float) -> float:
    probability = min(max(probability, 1.0e-6), 1.0 - 1.0e-6)
    return float(np.log(probability / (1.0 - probability)))


class ProbabilisticSEIRModel(BaseEpidemicModel):
    """Manual probabilistic SEIR baseline with Student-T observation noise."""

    df: int = 5

    def __init__(self, fit_config: FitConfig) -> None:
        super().__init__(fit_config)

    @property
    def model_name(self) -> str:
        return "probabilistic_seir"

    @property
    def compartment_names(self) -> tuple[str, ...]:
        return ("S", "E", "I", "R")

    @property
    def raw_parameter_dim(self) -> int:
        return 9

    def sample_initial_parameters(self, y_train: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        scale_guess = np.log(max(float(np.std(y_train)), 0.25))
        rho_guess = np.log(max(float(np.max(y_train)) / 0.01, 1.0))
        center = np.array(
            [
                -2.0,
                0.1,
                -0.1,
                _logit(0.25),
                _logit(0.35),
                rho_guess,
                scale_guess,
                -4.0,
                -5.0,
            ],
            dtype=float,
        )
        return center + rng.normal(loc=0.0, scale=0.75, size=center.size)

    def transform_parameters(self, raw_params: np.ndarray) -> dict[str, float]:
        init_simplex = softmax(np.array([0.0, raw_params[7], raw_params[8]], dtype=float))
        sigma = float(sigmoid(raw_params[3]))
        gamma = float(sigmoid(raw_params[4]))
        rho = float(np.exp(np.clip(raw_params[5], -12.0, 14.0)))
        obs_scale = float(np.exp(np.clip(raw_params[6], -12.0, 8.0)))
        return {
            "b0": float(raw_params[0]),
            "b1": float(raw_params[1]),
            "b2": float(raw_params[2]),
            "sigma": sigma,
            "gamma": gamma,
            "rho": rho,
            "obs_scale": obs_scale,
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

    def loss(self, y_true: np.ndarray, predictions: np.ndarray, raw_params: np.ndarray) -> float:
        params = self.transform_parameters(raw_params)
        nll = -np.sum(student_t.logpdf(y_true, df=self.df, loc=predictions, scale=params["obs_scale"]))
        prior = self.fit_config.prior_weight * float(np.sum(np.square(raw_params)))
        return float(nll + prior)

    def approximate_covariance(self, y_train: np.ndarray, fit_result: FitResult) -> np.ndarray:
        objective = lambda raw: self.objective(raw, y_train)
        hessian = finite_difference_hessian(objective, fit_result.raw_params)
        symmetric = 0.5 * (hessian + hessian.T)
        eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
        eigenvalues = np.clip(eigenvalues, 1.0e-6, None)
        covariance = eigenvectors @ np.diag(1.0 / eigenvalues) @ eigenvectors.T
        return covariance

    def _intervals_from_draws(self, trajectory_draws: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray]]:
        return {
            "50": (
                np.quantile(trajectory_draws, 0.25, axis=0),
                np.quantile(trajectory_draws, 0.75, axis=0),
            ),
            "80": (
                np.quantile(trajectory_draws, 0.10, axis=0),
                np.quantile(trajectory_draws, 0.90, axis=0),
            ),
            "95": (
                np.quantile(trajectory_draws, 0.025, axis=0),
                np.quantile(trajectory_draws, 0.975, axis=0),
            ),
        }

    def laplace_predictive_summary(
        self,
        y_train: np.ndarray,
        fit_result: FitResult,
        n_steps: int,
        rng: np.random.Generator,
        n_draws: int | None = None,
    ) -> dict[str, Any]:
        draw_count = self.fit_config.laplace_draws if n_draws is None else n_draws
        covariance = self.approximate_covariance(y_train, fit_result)
        proposal_variances = np.clip(np.diag(covariance), 1.0e-6, 0.25)
        proposal_covariance = np.diag(proposal_variances)
        raw_draws = rng.multivariate_normal(
            mean=fit_result.raw_params,
            cov=proposal_covariance,
            size=max(draw_count * 4, 100),
        )
        accepted_paths: list[np.ndarray] = []

        for raw_draw in raw_draws:
            with np.errstate(all="ignore"):
                draw_objective = self.objective(raw_draw, y_train)
                simulation = self.simulate(raw_draw, n_steps)
                params = self.transform_parameters(raw_draw)
                noise = rng.standard_t(df=self.df, size=n_steps) * params["obs_scale"]
                sampled_path = np.clip(simulation.predictions + noise, 0.0, None)

            if draw_objective <= fit_result.objective + 5.0 and np.all(np.isfinite(sampled_path)):
                accepted_paths.append(sampled_path)
            if len(accepted_paths) >= draw_count:
                break

        if not accepted_paths:
            map_simulation = self.simulate(fit_result.raw_params, n_steps)
            params = self.transform_parameters(fit_result.raw_params)
            fallback_noise = rng.standard_t(df=self.df, size=(draw_count, n_steps)) * params["obs_scale"]
            trajectory_draws = np.clip(map_simulation.predictions[None, :] + fallback_noise, 0.0, None)
        else:
            trajectory_draws = np.vstack(accepted_paths)

        return {
            "draws": trajectory_draws,
            "intervals": self._intervals_from_draws(trajectory_draws),
            "covariance": covariance,
            "method": "laplace",
            "draw_count": int(trajectory_draws.shape[0]),
            "point_forecast": self.simulate(fit_result.raw_params, n_steps).predictions.copy(),
        }

    def bootstrap_predictive_summary(
        self,
        y_train: np.ndarray,
        fit_result: FitResult,
        n_steps: int,
        rng: np.random.Generator,
        n_draws: int | None = None,
    ) -> dict[str, Any]:
        draw_count = self.fit_config.bootstrap_draws if n_draws is None else n_draws
        train_steps = len(y_train)
        base_scale = fit_result.params["obs_scale"]
        base_rollout = self.simulate(fit_result.raw_params, train_steps)
        accepted_paths: list[np.ndarray] = []

        for _ in range(draw_count):
            pseudo_train = np.clip(
                base_rollout.predictions + rng.standard_t(df=self.df, size=train_steps) * base_scale,
                0.0,
                None,
            )
            bootstrap_rng = np.random.default_rng(int(rng.integers(2**32 - 1)))
            try:
                bootstrap_fit = self.fit(
                    pseudo_train,
                    bootstrap_rng,
                    warm_start=fit_result.raw_params,
                    n_restarts=self.fit_config.bootstrap_n_restarts,
                )
                bootstrap_rollout = self.simulate(bootstrap_fit.raw_params, n_steps)
                bootstrap_noise = rng.standard_t(df=self.df, size=n_steps) * bootstrap_fit.params["obs_scale"]
                sampled_path = np.clip(bootstrap_rollout.predictions + bootstrap_noise, 0.0, None)
            except Exception:
                continue

            if np.all(np.isfinite(sampled_path)):
                accepted_paths.append(sampled_path)

        if not accepted_paths:
            fallback = self.laplace_predictive_summary(y_train, fit_result, n_steps, rng, n_draws=draw_count)
            fallback["method"] = "bootstrap_fallback_laplace"
            return fallback

        trajectory_draws = np.vstack(accepted_paths)
        return {
            "draws": trajectory_draws,
            "intervals": self._intervals_from_draws(trajectory_draws),
            "covariance": None,
            "method": "bootstrap",
            "draw_count": int(trajectory_draws.shape[0]),
            "point_forecast": self.simulate(fit_result.raw_params, n_steps).predictions.copy(),
        }

    def predictive_summary(
        self,
        y_train: np.ndarray,
        fit_result: FitResult,
        n_steps: int,
        rng: np.random.Generator,
        n_draws: int | None = None,
        method: str | None = None,
    ) -> dict[str, Any]:
        selected_method = (self.fit_config.uncertainty_method if method is None else method).lower()
        if selected_method == "bootstrap":
            return self.bootstrap_predictive_summary(y_train, fit_result, n_steps, rng, n_draws=n_draws)
        if selected_method == "laplace":
            return self.laplace_predictive_summary(y_train, fit_result, n_steps, rng, n_draws=n_draws)
        raise ValueError(f"Unsupported uncertainty method: {selected_method}")
