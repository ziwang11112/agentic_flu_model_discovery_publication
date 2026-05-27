from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data.split import ChronologicalSplit
from src.discovery.model import DiscoveryCompartmentModel, DiscoveryRegularizationConfig
from src.discovery.rules import StructureSpec
from src.discovery.search import (
    SearchConfig,
    SearchOutcome,
    evaluate_structure_candidate,
    run_exhaustive_structure_search,
    run_random_structure_search,
)
from src.evaluation.pipeline import run_validation_only_discovery_family
from src.models.base import FitConfig, FitResult, SimulationResult


def test_stability_aware_score_preserves_existing_formula(monkeypatch) -> None:
    _patch_discovery_model(monkeypatch)
    spec = StructureSpec("SEIR", fractional=False, observation_map="I")
    config = SearchConfig(score_multi_split_std_weight=0.5, score_stability_weight=0.2)

    record = evaluate_structure_candidate(
        series_name="Overall",
        spec=spec,
        y_train=np.asarray([1.0, 1.2, 1.4, 1.6]),
        y_val=np.asarray([1.8, 2.0]),
        fit_config=FitConfig(n_restarts=1, maxiter=5),
        search_config=config,
        regularization_config=DiscoveryRegularizationConfig(),
        seed=42,
        score_policy="stability_aware",
        round_idx=1,
    )

    expected = (
        record["multi_split_val_mean_mae"]
        + record["multi_split_penalty"]
        + record["stability_penalty"]
        + record["complexity_penalty"]
        + record["age_prior_penalty"]
    )
    assert np.isclose(record["score"], expected)
    assert record["score_used_multi_split"] is True
    assert record["score_used_stability"] is True


def test_validation_only_score_equals_val_mae(monkeypatch) -> None:
    _patch_discovery_model(monkeypatch)
    record = evaluate_structure_candidate(
        series_name="Overall",
        spec=StructureSpec("SEIRS", fractional=True, observation_map="I"),
        y_train=np.asarray([1.0, 1.2, 1.4, 1.6]),
        y_val=np.asarray([1.8, 2.0]),
        fit_config=FitConfig(n_restarts=1, maxiter=5),
        search_config=SearchConfig(),
        regularization_config=DiscoveryRegularizationConfig(),
        seed=42,
        score_policy="validation_only",
    )

    assert record["score"] == record["val_mae"]
    assert record["score_used_val_mae"] is True
    assert record["score_used_complexity"] is False
    assert record["score_used_age_prior"] is False


def test_no_stability_score_excludes_stability_penalty_but_records_it(monkeypatch) -> None:
    _patch_discovery_model(monkeypatch)
    record = evaluate_structure_candidate(
        series_name="Overall",
        spec=StructureSpec("SEIR", fractional=False, observation_map="I"),
        y_train=np.asarray([1.0, 1.2, 1.4, 1.6]),
        y_val=np.asarray([1.8, 2.0]),
        fit_config=FitConfig(n_restarts=1, maxiter=5),
        search_config=SearchConfig(score_stability_weight=10.0),
        regularization_config=DiscoveryRegularizationConfig(),
        seed=42,
        score_policy="no_stability",
    )

    expected = (
        record["multi_split_val_mean_mae"]
        + record["multi_split_penalty"]
        + record["complexity_penalty"]
        + record["age_prior_penalty"]
    )
    assert np.isclose(record["score"], expected)
    assert record["stability_penalty"] > 0.0
    assert record["score_used_stability"] is False


def test_random_repeats_do_not_deduplicate_specs(monkeypatch, tmp_path: Path) -> None:
    spec = StructureSpec("SEIR", fractional=False, observation_map="I")
    monkeypatch.setattr("src.discovery.search.enumerate_valid_structure_specs", lambda: [spec])
    monkeypatch.setattr("src.discovery.search.evaluate_structure_candidate", _fake_candidate_record)

    outcome = run_random_structure_search(
        series_name="Overall",
        y_train=np.asarray([1.0, 1.1, 1.2]),
        y_val=np.asarray([1.3]),
        fit_config=FitConfig(),
        search_config=SearchConfig(random_candidate_budget=1, random_repeats=2),
        artifact_dir=tmp_path,
        seed=42,
    )

    assert len(outcome.leaderboard) == 2
    assert outcome.leaderboard["spec_key"].tolist() == [spec.spec_key, spec.spec_key]
    assert sorted(outcome.leaderboard["record_key"].tolist()) == [f"0:{spec.spec_key}", f"1:{spec.spec_key}"]
    assert outcome.best_record["search_metadata"]["random_repeats"] == 2


def test_exhaustive_search_writes_leaderboard_and_best_spec(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "src.discovery.search.enumerate_valid_structure_specs",
        lambda: [
            StructureSpec("SEIR", fractional=False, observation_map="I"),
            StructureSpec("SIR", fractional=False, observation_map="I"),
        ],
    )
    monkeypatch.setattr("src.discovery.search.evaluate_structure_candidate", _fake_candidate_record)

    outcome = run_exhaustive_structure_search(
        series_name="Overall",
        y_train=np.asarray([1.0, 1.1, 1.2]),
        y_val=np.asarray([1.3]),
        fit_config=FitConfig(),
        search_config=SearchConfig(),
        artifact_dir=tmp_path,
        seed=42,
    )

    assert (tmp_path / "leaderboard.csv").exists()
    assert (tmp_path / "best_model_spec.json").exists()
    assert outcome.best_spec.spec_key in set(outcome.leaderboard["spec_key"])


def test_validation_only_family_wrapper_writes_final_artifacts(monkeypatch, tmp_path: Path) -> None:
    _patch_discovery_model(monkeypatch)
    monkeypatch.setattr(
        "src.evaluation.pipeline.run_validation_only_structure_selection",
        lambda **kwargs: SearchOutcome(
            best_spec=StructureSpec("SEIR", fractional=False, observation_map="I"),
            leaderboard=pd.DataFrame(
                [
                    {
                        "spec_key": "SEIR|fractional=0|obs=I",
                        "score": 0.0,
                    }
                ]
            ),
            best_record={"spec_key": "SEIR|fractional=0|obs=I", "score_policy": "validation_only"},
        ),
    )
    y = np.asarray([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])

    result = run_validation_only_discovery_family(
        y=y,
        series_name="Overall",
        split=ChronologicalSplit(train_end=3, val_end=5, n_obs=len(y)),
        fit_config=FitConfig(n_restarts=1, rolling_n_restarts=0, maxiter=5),
        search_config=SearchConfig(rolling_horizons=(1,)),
        horizons=[1],
        artifact_dir=tmp_path,
        seed=42,
    )

    assert result["comparison_row"]["model_name"] == "validation_only_structure_selection"
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "forecast_trace.csv").exists()
    assert (tmp_path / "rolling_origin_forecasts.csv").exists()


def _patch_discovery_model(monkeypatch) -> None:
    def fake_fit(self, y_train, rng, warm_start=None, n_restarts=None):
        del rng, warm_start, n_restarts
        raw_params = np.zeros(self.raw_parameter_dim, dtype=float)
        simulation = self.simulate(raw_params, len(y_train))
        return FitResult(
            model_name=self.model_name,
            raw_params=raw_params,
            params=self.transform_parameters(raw_params),
            simulation=simulation,
            objective=0.0,
            success=True,
            message="ok",
            param_count=self.raw_parameter_dim,
        )

    def fake_simulate(self, raw_params, n_steps):
        del raw_params
        states = np.full((n_steps, len(self.compartment_names)), 0.05, dtype=float)
        predictions = np.linspace(1.0, 1.0 + 0.1 * max(n_steps - 1, 0), n_steps)
        return SimulationResult(
            compartments=self.compartment_names,
            states=states,
            predictions=predictions,
            penalties={"negative": 0.0, "mass": 0.0},
        )

    monkeypatch.setattr(DiscoveryCompartmentModel, "fit", fake_fit)
    monkeypatch.setattr(DiscoveryCompartmentModel, "simulate", fake_simulate)


def _fake_candidate_record(**kwargs):
    spec = kwargs["spec"]
    repeat_idx = kwargs.get("repeat_idx")
    score = 0.1 if spec.structure_name == "SIR" else 0.2
    return {
        "round": kwargs.get("round_idx"),
        "repeat": repeat_idx,
        "record_key": f"{repeat_idx}:{spec.spec_key}" if repeat_idx is not None else spec.spec_key,
        "spec_key": spec.spec_key,
        "structure_name": spec.structure_name,
        "fractional": spec.fractional,
        "observation_map": spec.observation_map,
        "delay_weeks": int(spec.delay_weeks),
        "score": score,
        "score_policy": kwargs.get("score_policy", "stability_aware"),
        "score_formula": "fake",
        "val_mae": score,
        "rolling_val_mean_mae": score,
        "multi_split_val_mean_mae": score,
        "multi_split_val_std_mae": 0.0,
        "stability_penalty": 0.0,
        "complexity_penalty": 0.0,
        "age_prior_penalty": 0.0,
        "score_used_val_mae": False,
        "score_used_multi_split": True,
        "score_used_stability": True,
        "score_used_complexity": True,
        "score_used_age_prior": True,
        "params": {},
    }
