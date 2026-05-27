from __future__ import annotations

from run_experiment import _fit_config


def test_benchmark_level_conformal_disables_fitting_interval_calibration() -> None:
    config = {
        "seed": 42,
        "fitting": {
            "n_restarts": 1,
            "rolling_n_restarts": 1,
            "maxiter": 10,
            "negative_penalty": 1.0,
            "mass_penalty": 1.0,
            "prior_weight": 0.0,
            "laplace_draws": 10,
            "uncertainty_method": "bootstrap",
            "bootstrap_draws": 30,
            "bootstrap_n_restarts": 0,
            "calibrate_intervals": True,
            "interval_calibration_method": "conformal",
            "calibration_draws": 12,
            "calibration_scale_min": 0.25,
            "calibration_scale_max": 1.25,
            "calibration_scale_grid_size": 41,
        },
        "uncertainty": {
            "conformal": {
                "enabled": True,
            }
        },
    }

    fit_config = _fit_config(config)

    assert fit_config.calibrate_intervals is False
    assert fit_config.uncertainty_method == "bootstrap"
