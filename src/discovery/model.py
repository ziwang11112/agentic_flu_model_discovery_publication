from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.discovery.rules import StructureSpec, structure_template
from src.models.base import BaseEpidemicModel, FitConfig, SimulationResult
from src.models.simulators import caputo_l1_simulation, euler_discrete_simulation
from src.utils.math_utils import seasonal_beta, sigmoid, softmax


def _logit(probability: float) -> float:
    probability = min(max(probability, 1.0e-6), 1.0 - 1.0e-6)
    return float(np.log(probability / (1.0 - probability)))


@dataclass(frozen=True)
class DiscoveryRegularizationConfig:
    """Extra regularization for discovery-time model fitting."""

    raw_l2_weight: float = 5.0e-4
    seasonality_l2_weight: float = 5.0e-3
    rho_l2_weight: float = 2.0e-3
    init_l2_weight: float = 2.0e-3
    fractional_alpha_weight: float = 2.0e-3


class DiscoveryCompartmentModel(BaseEpidemicModel):
    """Parameterized compartment model used inside constrained structure discovery."""

    def __init__(
        self,
        spec: StructureSpec,
        fit_config: FitConfig,
        regularization_config: DiscoveryRegularizationConfig | None = None,
    ) -> None:
        super().__init__(fit_config)
        self.spec = spec
        self.regularization_config = (
            DiscoveryRegularizationConfig()
            if regularization_config is None
            else regularization_config
        )

    @property
    def model_name(self) -> str:
        return f"discovery_{self.spec.slug}"

    @property
    def compartment_names(self) -> tuple[str, ...]:
        return structure_template(self.spec)["compartments"]

    @property
    def raw_parameter_dim(self) -> int:
        count = 3 + len(self._rate_names()) + 1 + len(self._init_names())
        if self.spec.fractional:
            count += 1
        return count

    def _rate_names(self) -> list[str]:
        mapping = {
            "SIR": ["gamma"],
            "SEIR": ["sigma", "gamma"],
            "SEIRS": ["sigma", "gamma", "omega"],
            "SEIHR": ["sigma", "eta", "gamma_i", "gamma_h"],
            "SEIAR": ["sigma", "p_asym", "gamma_i", "gamma_a"],
        }
        return mapping[self.spec.structure_name]

    def _init_names(self) -> list[str]:
        mapping = {
            "SIR": ["I0"],
            "SEIR": ["E0", "I0"],
            "SEIRS": ["E0", "I0"],
            "SEIHR": ["E0", "I0", "H0"],
            "SEIAR": ["E0", "I0", "A0"],
        }
        return mapping[self.spec.structure_name]

    def sample_initial_parameters(self, y_train: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        rho_guess = np.log(max(float(np.max(y_train)) / 0.01, 1.0))
        center = [ -2.0, 0.1, -0.1 ]
        for name in self._rate_names():
            if name == "p_asym":
                center.append(_logit(0.30))
            elif name == "omega":
                center.append(_logit(0.05))
            else:
                center.append(_logit(0.30))
        center.append(rho_guess)
        if self.spec.fractional:
            center.append(1.5)
        center.extend([-4.0 - idx for idx, _ in enumerate(self._init_names())])
        return np.array(center, dtype=float) + rng.normal(loc=0.0, scale=0.8, size=len(center))

    def transform_parameters(self, raw_params: np.ndarray) -> dict[str, float]:
        cursor = 0
        params: dict[str, float] = {
            "b0": float(raw_params[cursor]),
            "b1": float(raw_params[cursor + 1]),
            "b2": float(raw_params[cursor + 2]),
        }
        cursor += 3

        for name in self._rate_names():
            value = float(sigmoid(raw_params[cursor]))
            params[name] = value
            cursor += 1

        params["rho"] = float(np.exp(np.clip(raw_params[cursor], -12.0, 14.0)))
        cursor += 1

        if self.spec.fractional:
            params["alpha"] = float(0.7 + 0.3 * sigmoid(raw_params[cursor]))
            cursor += 1

        init_logits = np.concatenate(([0.0], raw_params[cursor : cursor + len(self._init_names())]))
        init_simplex = softmax(init_logits.astype(float))
        params["S0"] = float(init_simplex[0])
        for name, value in zip(self._init_names(), init_simplex[1:]):
            params[name] = float(value)
        params["R0"] = 0.0
        params["fractional"] = float(self.spec.fractional)
        return params

    def _drift(self, state: np.ndarray, t: int, params: dict[str, float]) -> np.ndarray:
        beta_t = float(seasonal_beta(t, params["b0"], params["b1"], params["b2"]))

        if self.spec.structure_name == "SIR":
            s_val, i_val, _ = state
            infection = beta_t * s_val * i_val
            return np.array([-infection, infection - params["gamma"] * i_val, params["gamma"] * i_val], dtype=float)

        if self.spec.structure_name == "SEIR":
            s_val, e_val, i_val, _ = state
            infection = beta_t * s_val * i_val
            return np.array(
                [-infection, infection - params["sigma"] * e_val, params["sigma"] * e_val - params["gamma"] * i_val, params["gamma"] * i_val],
                dtype=float,
            )

        if self.spec.structure_name == "SEIRS":
            s_val, e_val, i_val, r_val = state
            infection = beta_t * s_val * i_val
            return np.array(
                [
                    -infection + params["omega"] * r_val,
                    infection - params["sigma"] * e_val,
                    params["sigma"] * e_val - params["gamma"] * i_val,
                    params["gamma"] * i_val - params["omega"] * r_val,
                ],
                dtype=float,
            )

        if self.spec.structure_name == "SEIHR":
            s_val, e_val, i_val, h_val, _ = state
            infection = beta_t * s_val * i_val
            hosp_flow = params["eta"] * i_val
            direct_recovery = params["gamma_i"] * i_val
            discharge_flow = params["gamma_h"] * h_val
            return np.array(
                [
                    -infection,
                    infection - params["sigma"] * e_val,
                    params["sigma"] * e_val - hosp_flow - direct_recovery,
                    hosp_flow - discharge_flow,
                    direct_recovery + discharge_flow,
                ],
                dtype=float,
            )

        if self.spec.structure_name == "SEIAR":
            s_val, e_val, i_val, a_val, _ = state
            force = i_val + 0.5 * a_val
            infection = beta_t * s_val * force
            exposed_out = params["sigma"] * e_val
            return np.array(
                [
                    -infection,
                    infection - exposed_out,
                    (1.0 - params["p_asym"]) * exposed_out - params["gamma_i"] * i_val,
                    params["p_asym"] * exposed_out - params["gamma_a"] * a_val,
                    params["gamma_i"] * i_val + params["gamma_a"] * a_val,
                ],
                dtype=float,
            )

        raise KeyError(f"Unsupported structure {self.spec.structure_name}")

    def discovery_regularization_penalty(self, raw_params: np.ndarray) -> float:
        """Regularize discovery fits away from unstable extreme parameters."""
        config = self.regularization_config
        penalty = 0.0
        penalty += config.raw_l2_weight * float(np.sum(np.square(raw_params)))
        penalty += config.seasonality_l2_weight * float(np.sum(np.square(raw_params[1:3])))

        rho_index = 3 + len(self._rate_names())
        penalty += config.rho_l2_weight * float(raw_params[rho_index] ** 2)

        init_start = rho_index + 1 + int(self.spec.fractional)
        penalty += config.init_l2_weight * float(np.sum(np.square(raw_params[init_start:])))

        if self.spec.fractional:
            alpha_index = rho_index + 1
            alpha = 0.7 + 0.3 * sigmoid(raw_params[alpha_index])
            penalty += config.fractional_alpha_weight * float((1.0 - alpha) ** 2)

        return float(penalty)

    def objective(self, raw_params: np.ndarray, y_train: np.ndarray) -> float:
        base_objective = super().objective(raw_params, y_train)
        if not np.isfinite(base_objective):
            return base_objective
        return float(base_objective + self.discovery_regularization_penalty(raw_params))

    def simulate(self, raw_params: np.ndarray, n_steps: int) -> SimulationResult:
        params = self.transform_parameters(raw_params)
        if self.spec.structure_name == "SIR":
            initial_state = np.array([params["S0"], params["I0"], params["R0"]], dtype=float)
        elif self.spec.structure_name in {"SEIR", "SEIRS"}:
            initial_state = np.array([params["S0"], params["E0"], params["I0"], params["R0"]], dtype=float)
        elif self.spec.structure_name == "SEIHR":
            initial_state = np.array([params["S0"], params["E0"], params["I0"], params["H0"], params["R0"]], dtype=float)
        elif self.spec.structure_name == "SEIAR":
            initial_state = np.array([params["S0"], params["E0"], params["I0"], params["A0"], params["R0"]], dtype=float)
        else:
            raise KeyError(f"Unsupported structure {self.spec.structure_name}")

        drift_fn = lambda state, t: self._drift(state, t, params)
        if self.spec.fractional:
            states = caputo_l1_simulation(initial_state, n_steps, params["alpha"], drift_fn)
        else:
            states = euler_discrete_simulation(initial_state, n_steps, drift_fn)

        index_map = {name: idx for idx, name in enumerate(self.compartment_names)}
        if self.spec.observation_map == "I":
            observed_state = states[:, index_map["I"]]
        elif self.spec.observation_map == "H":
            observed_state = states[:, index_map["H"]]
        elif self.spec.observation_map == "I+H":
            observed_state = states[:, index_map["I"]] + states[:, index_map["H"]]
        elif self.spec.observation_map == "delayed_I":
            delayed_i = np.zeros(n_steps, dtype=float)
            delay = int(self.spec.delay_weeks)
            for t in range(n_steps):
                delayed_i[t] = states[max(t - delay, 0), index_map["I"]]
            observed_state = delayed_i
        else:
            raise ValueError(f"Unsupported observation map: {self.spec.observation_map}")
        predictions = params["rho"] * observed_state

        return SimulationResult(
            compartments=self.compartment_names,
            states=states,
            predictions=predictions,
            penalties=self.penalty_summary(states),
        )
