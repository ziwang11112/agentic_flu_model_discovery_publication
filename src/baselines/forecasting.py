from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ForecastBaselineConfig:
    lags: tuple[int, ...] = (1, 2, 4)
    rolling_mean_windows: tuple[int, ...] = (2, 4)
    arima_orders: tuple[tuple[int, int, int], ...] = ((1, 0, 0), (1, 1, 0), (0, 1, 1), (1, 1, 1))
    gbr_random_state: int = 42


@dataclass
class ForecastBaseline:
    model_name: str
    num_free_params: int = 0
    num_compartments: int = 0
    uses_validation_selection: bool = False
    fallback_used: bool = False
    fallback_model_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def fit(self, y_train: np.ndarray, y_val: np.ndarray | None = None) -> ForecastBaseline:
        raise NotImplementedError

    def predict(self, n_steps: int) -> np.ndarray:
        raise NotImplementedError

    def fitted_values(self, y: np.ndarray) -> np.ndarray:
        return _last_observed_fitted_values(np.asarray(y, dtype=float))


@dataclass
class LastObservedBaseline(ForecastBaseline):
    model_name: str = "last_observed"

    def fit(self, y_train: np.ndarray, y_val: np.ndarray | None = None) -> LastObservedBaseline:
        history = np.asarray(y_train if y_val is None else np.concatenate([y_train, y_val]), dtype=float)
        self.metadata = {"train_length": int(len(history))}
        self._last_value = float(history[-1]) if len(history) else 0.0
        return self

    def predict(self, n_steps: int) -> np.ndarray:
        return np.full(int(n_steps), self._last_value, dtype=float)


@dataclass
class RollingMeanBaseline(ForecastBaseline):
    window: int = 4
    model_name: str = "rolling_mean_4wk"

    def fit(self, y_train: np.ndarray, y_val: np.ndarray | None = None) -> RollingMeanBaseline:
        history = np.asarray(y_train if y_val is None else np.concatenate([y_train, y_val]), dtype=float)
        self.metadata = {"window": int(self.window), "train_length": int(len(history))}
        if len(history) == 0:
            self._mean_value = 0.0
        else:
            self._mean_value = float(np.mean(history[-min(self.window, len(history)) :]))
        return self

    def predict(self, n_steps: int) -> np.ndarray:
        return np.full(int(n_steps), self._mean_value, dtype=float)

    def fitted_values(self, y: np.ndarray) -> np.ndarray:
        values = np.asarray(y, dtype=float)
        predictions = np.zeros_like(values, dtype=float)
        for index in range(len(values)):
            if index == 0:
                predictions[index] = values[index]
            else:
                window_values = values[max(0, index - self.window) : index]
                predictions[index] = float(np.mean(window_values))
        return predictions


@dataclass
class ARIMAAutoSmallBaseline(ForecastBaseline):
    config: ForecastBaselineConfig = field(default_factory=ForecastBaselineConfig)
    model_name: str = "arima_auto_small"
    uses_validation_selection: bool = True

    def fit(self, y_train: np.ndarray, y_val: np.ndarray | None = None) -> ARIMAAutoSmallBaseline:
        train = np.asarray(y_train, dtype=float)
        validation = None if y_val is None else np.asarray(y_val, dtype=float)
        self.metadata = {"candidate_orders": [list(order) for order in self.config.arima_orders]}
        self.fallback_used = False
        self.fallback_model_name = None
        self._fallback = None
        self._fit_result = None
        self._selected_order = None
        self.validation_predictions_ = None

        if len(train) < 6:
            return self._use_fallback(train, validation, "too_few_observations")

        selection_train = train
        selection_val = validation
        fit_history = train if validation is None else np.concatenate([train, validation])
        if selection_val is None and len(train) >= 8:
            holdout = max(1, min(4, len(train) // 5))
            selection_train = train[:-holdout]
            selection_val = train[-holdout:]

        selected_order = None
        best_mae = float("inf")
        best_validation_predictions = None
        if selection_val is not None and len(selection_val) > 0:
            for order in self.config.arima_orders:
                fit_result = _fit_arima(selection_train, order)
                if fit_result is None:
                    continue
                try:
                    forecast = np.asarray(fit_result.forecast(steps=len(selection_val)), dtype=float)
                except Exception:
                    continue
                if len(forecast) != len(selection_val) or not np.all(np.isfinite(forecast)):
                    continue
                mae = float(np.mean(np.abs(selection_val - forecast)))
                if (mae, order) < (best_mae, selected_order or order):
                    best_mae = mae
                    selected_order = order
                    best_validation_predictions = forecast

        if selected_order is None:
            for order in self.config.arima_orders:
                if _fit_arima(fit_history, order) is not None:
                    selected_order = order
                    break

        if selected_order is None:
            return self._use_fallback(train, validation, "all_candidate_orders_failed")

        fit_result = _fit_arima(fit_history, selected_order)
        if fit_result is None:
            return self._use_fallback(train, validation, "selected_order_refit_failed")

        self._fit_result = fit_result
        self._selected_order = selected_order
        self.num_free_params = int(sum(selected_order) + 1)
        self.validation_predictions_ = best_validation_predictions if validation is not None else None
        self.metadata.update(
            {
                "selected_order": list(selected_order),
                "validation_mae": None if not np.isfinite(best_mae) else best_mae,
                "fallback_used": False,
            }
        )
        return self

    def predict(self, n_steps: int) -> np.ndarray:
        if self._fallback is not None:
            return self._fallback.predict(n_steps)
        try:
            return np.asarray(self._fit_result.forecast(steps=int(n_steps)), dtype=float)
        except Exception:
            self.fallback_used = True
            self.fallback_model_name = "last_observed"
            self.metadata["fallback_used"] = True
            self.metadata["fallback_reason"] = "forecast_failed"
            return self._fallback_from_result().predict(n_steps)

    def _use_fallback(
        self,
        y_train: np.ndarray,
        y_val: np.ndarray | None,
        reason: str,
    ) -> ARIMAAutoSmallBaseline:
        self.fallback_used = True
        self.fallback_model_name = "last_observed"
        self._fallback = LastObservedBaseline().fit(y_train, y_val)
        self.metadata.update({"fallback_used": True, "fallback_reason": reason})
        if y_val is not None:
            self.validation_predictions_ = LastObservedBaseline().fit(y_train).predict(len(y_val))
        return self

    def _fallback_from_result(self) -> LastObservedBaseline:
        if self._fallback is not None:
            return self._fallback
        return LastObservedBaseline().fit(np.asarray([0.0]))


@dataclass
class _LaggedRegressionBaseline(ForecastBaseline):
    config: ForecastBaselineConfig = field(default_factory=ForecastBaselineConfig)
    min_samples: int = 3

    def fit(self, y_train: np.ndarray, y_val: np.ndarray | None = None) -> _LaggedRegressionBaseline:
        history = np.asarray(y_train if y_val is None else np.concatenate([y_train, y_val]), dtype=float)
        self._history = history
        self._fallback = None
        self._model = None
        self.fallback_used = False
        self.fallback_model_name = None
        self.metadata = {
            "lags": list(self.config.lags),
            "train_length": int(len(history)),
            "fallback_used": False,
        }

        max_lag = max(self.config.lags)
        sample_count = max(0, len(history) - max_lag)
        if sample_count < self.min_samples:
            return self._use_fallback(history, "too_few_training_samples")

        try:
            model = self._new_model()
            features, targets = _lagged_design_matrix(history, self.config.lags)
            model.fit(features, targets)
        except Exception as exc:
            return self._use_fallback(history, f"fit_failed:{type(exc).__name__}")

        self._model = model
        self.num_free_params = int(features.shape[1])
        return self

    def predict(self, n_steps: int) -> np.ndarray:
        if self._fallback is not None:
            return self._fallback.predict(n_steps)
        history = [float(value) for value in self._history]
        predictions: list[float] = []
        for _ in range(int(n_steps)):
            target_t = len(history)
            features = _lagged_features(np.asarray(history, dtype=float), target_t, self.config.lags)
            prediction = float(self._model.predict(features.reshape(1, -1))[0])
            predictions.append(prediction)
            history.append(prediction)
        return np.asarray(predictions, dtype=float)

    def fitted_values(self, y: np.ndarray) -> np.ndarray:
        values = np.asarray(y, dtype=float)
        if self._fallback is not None or self._model is None:
            return RollingMeanBaseline(window=4).fitted_values(values)
        predictions = RollingMeanBaseline(window=4).fitted_values(values)
        max_lag = max(self.config.lags)
        for target_t in range(max_lag, len(values)):
            features = _lagged_features(values, target_t, self.config.lags)
            predictions[target_t] = float(self._model.predict(features.reshape(1, -1))[0])
        return predictions

    def _use_fallback(self, history: np.ndarray, reason: str) -> _LaggedRegressionBaseline:
        self.fallback_used = True
        self.fallback_model_name = "rolling_mean_4wk"
        self._fallback = RollingMeanBaseline(window=4).fit(history)
        self.metadata.update({"fallback_used": True, "fallback_reason": reason})
        return self

    def _new_model(self) -> Any:
        raise NotImplementedError


@dataclass
class LaggedRidgeBaseline(_LaggedRegressionBaseline):
    model_name: str = "lagged_ridge"
    min_samples: int = 3

    def _new_model(self) -> Any:
        from sklearn.linear_model import Ridge

        return Ridge(alpha=1.0)


@dataclass
class LaggedGradientBoostingBaseline(_LaggedRegressionBaseline):
    model_name: str = "lagged_gradient_boosting"
    min_samples: int = 8

    def _new_model(self) -> Any:
        from sklearn.ensemble import GradientBoostingRegressor

        return GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=2,
            random_state=int(self.config.gbr_random_state),
        )


FORECAST_BASELINE_NAMES = {
    "last_observed",
    "rolling_mean_2wk",
    "rolling_mean_4wk",
    "arima_auto_small",
    "lagged_ridge",
    "lagged_gradient_boosting",
}


def create_forecast_baseline(
    model_name: str,
    seed: int = 42,
    config: ForecastBaselineConfig | None = None,
) -> ForecastBaseline:
    baseline_config = config or ForecastBaselineConfig(gbr_random_state=seed)
    if model_name == "last_observed":
        return LastObservedBaseline()
    if model_name == "rolling_mean_2wk":
        return RollingMeanBaseline(window=2, model_name="rolling_mean_2wk")
    if model_name == "rolling_mean_4wk":
        return RollingMeanBaseline(window=4, model_name="rolling_mean_4wk")
    if model_name == "arima_auto_small":
        return ARIMAAutoSmallBaseline(config=baseline_config)
    if model_name == "lagged_ridge":
        return LaggedRidgeBaseline(config=baseline_config)
    if model_name == "lagged_gradient_boosting":
        return LaggedGradientBoostingBaseline(config=baseline_config)
    raise ValueError(f"Unsupported forecast baseline: {model_name}")


def _last_observed_fitted_values(y: np.ndarray) -> np.ndarray:
    values = np.asarray(y, dtype=float)
    if len(values) == 0:
        return np.asarray([], dtype=float)
    predictions = np.empty_like(values, dtype=float)
    predictions[0] = values[0]
    if len(values) > 1:
        predictions[1:] = values[:-1]
    return predictions


def _lagged_design_matrix(y: np.ndarray, lags: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(y, dtype=float)
    max_lag = max(lags)
    rows = [_lagged_features(values, target_t, lags) for target_t in range(max_lag, len(values))]
    targets = values[max_lag:]
    return np.vstack(rows), targets


def _lagged_features(y: np.ndarray, target_t: int, lags: tuple[int, ...]) -> np.ndarray:
    lag_values = [float(y[target_t - lag]) for lag in lags]
    seasonal_angle = 2.0 * np.pi * float(target_t) / 52.0
    return np.asarray(
        [
            *lag_values,
            float(target_t),
            float(np.sin(seasonal_angle)),
            float(np.cos(seasonal_angle)),
        ],
        dtype=float,
    )


def _fit_arima(y: np.ndarray, order: tuple[int, int, int]) -> Any | None:
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except Exception:
        return None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return ARIMA(
                np.asarray(y, dtype=float),
                order=order,
                enforce_stationarity=False,
                enforce_invertibility=False,
            ).fit()
    except Exception:
        return None
