from __future__ import annotations

from src.discovery.candidates import enumerate_valid_structure_specs
from src.discovery.rules import StructureSpec, validate_structure


def test_enumerated_specs_are_valid_and_sorted() -> None:
    specs = enumerate_valid_structure_specs()

    assert specs == sorted(specs, key=lambda spec: spec.spec_key)
    assert all(validate_structure(spec).valid for spec in specs)


def test_invalid_h_observation_specs_are_filtered_for_non_seihr() -> None:
    specs = enumerate_valid_structure_specs()

    assert not any(spec.structure_name != "SEIHR" and spec.observation_map in {"H", "I+H"} for spec in specs)


def test_no_observation_universe_only_contains_i_observation() -> None:
    specs = [spec for spec in enumerate_valid_structure_specs() if spec.observation_map == "I"]

    assert specs
    assert {spec.observation_map for spec in specs} == {"I"}


def test_delayed_i_delay_zero_is_excluded_to_avoid_duplicate_i() -> None:
    specs = enumerate_valid_structure_specs()

    assert StructureSpec("SEIR", fractional=False, observation_map="delayed_I", delay_weeks=0) not in specs
