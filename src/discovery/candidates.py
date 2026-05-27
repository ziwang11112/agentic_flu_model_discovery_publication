from __future__ import annotations

from src.discovery.rules import StructureSpec, validate_structure


def enumerate_valid_structure_specs(
    *,
    structures: tuple[str, ...] = ("SIR", "SEIR", "SEIRS", "SEIHR", "SEIAR"),
    fractional_options: tuple[bool, ...] = (False, True),
    observation_maps: tuple[str, ...] = ("I", "H", "I+H", "delayed_I"),
    delay_candidates: tuple[int, ...] = (1, 2, 3),
) -> list[StructureSpec]:
    """Enumerate the constrained discovery grammar in deterministic order."""
    candidates: list[StructureSpec] = []
    for structure_name in structures:
        for fractional in fractional_options:
            for observation_map in observation_maps:
                delays = delay_candidates if observation_map == "delayed_I" else (0,)
                for delay_weeks in delays:
                    spec = StructureSpec(
                        structure_name=structure_name,
                        fractional=bool(fractional),
                        observation_map=observation_map,
                        delay_weeks=int(delay_weeks),
                    )
                    if validate_structure(spec).valid:
                        candidates.append(spec)

    return sorted({candidate.spec_key: candidate for candidate in candidates}.values(), key=lambda spec: spec.spec_key)
