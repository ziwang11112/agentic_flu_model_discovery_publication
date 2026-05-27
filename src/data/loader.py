from __future__ import annotations

from pathlib import Path
from typing import Iterable
import warnings

import pandas as pd

PRIMARY_FILTERS = {
    "CATCHMENT": "Entire Network",
    "AGE CATEGORY": "Overall",
    "SEX CATEGORY": "Overall",
    "RACE CATEGORY": "Overall",
    "VIRUS TYPE CATEGORY": "Overall",
}

ROBUSTNESS_AGE_GROUPS = ["0-4 yr", "5-17 yr", "18-49 yr", "50-64 yr", ">= 65 yr"]
SEASON_MODE_POOLED = "pooled"
SEASON_MODE_SEPARATE = "separate"
POOLED_MULTI_SEASON_WARNING = (
    "pooled multi-season mode concatenates selected FluSurv-NET seasons into one chronological "
    "sequence. Use it only for smoke/descriptive runs; use season_mode='separate' or an explicit "
    "season-level train/validation/test split for paper-level claims."
)


def resolve_data_path(repo_root: Path, configured_path: str | Path) -> Path:
    """Resolve a configured data path, falling back to data/raw for bare filenames."""
    path = Path(configured_path)
    candidates = [path] if path.is_absolute() else [repo_root / path]
    if not path.is_absolute() and path.parent == Path("."):
        candidates.append(repo_root / "data" / "raw" / path.name)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def normalize_flu_season_label(value: object) -> str:
    """Normalize FluSurv-NET season labels such as 2023-24."""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def available_flu_seasons(frame: pd.DataFrame) -> list[str]:
    """Return sorted season labels present in a loaded FluSurv-NET frame."""
    if "season" in frame.columns:
        values = frame["season"]
    else:
        values = frame["YEAR"]
    seasons = {normalize_flu_season_label(value) for value in values.dropna().tolist()}
    return sorted(seasons)


def _normalize_requested_seasons(seasons: Iterable[str] | None) -> tuple[str, ...]:
    if seasons is None:
        return ()
    return tuple(normalize_flu_season_label(season) for season in seasons)


def _season_mask(frame: pd.DataFrame, seasons: Iterable[str] | None) -> pd.Series:
    requested = set(_normalize_requested_seasons(seasons))
    if not requested:
        return pd.Series(True, index=frame.index)
    season_values = frame["season"] if "season" in frame.columns else frame["YEAR"]
    normalized = season_values.map(normalize_flu_season_label)
    return normalized.isin(requested)


def _validate_season_mode(season_mode: str) -> str:
    normalized = str(season_mode).strip().lower()
    if normalized in {SEASON_MODE_POOLED, "pool"}:
        return SEASON_MODE_POOLED
    if normalized in {SEASON_MODE_SEPARATE, "seasonal", "by_season"}:
        return SEASON_MODE_SEPARATE
    raise ValueError(f"Unsupported season_mode={season_mode!r}; expected pooled or separate.")


def format_flu_series_name(age_category: str, season: str | None = None) -> str:
    """Format a display name for an age category, optionally scoped to one season."""
    return age_category if season is None else f"{season} / {age_category}"


def load_flu_surv_data(csv_path: str | Path) -> pd.DataFrame:
    """Load the FluSurv-NET export and normalize its weekly index."""
    frame = pd.read_csv(csv_path, skiprows=2)
    frame.columns = [column.strip() for column in frame.columns]
    frame = frame.dropna(subset=["WEEK", "YEAR.1"]).copy()

    numeric_columns = ["WEEK", "YEAR.1", "WEEKLY RATE", "CUMULATIVE RATE"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=["WEEK", "YEAR.1", "WEEKLY RATE"]).copy()
    frame["WEEK"] = frame["WEEK"].astype(int)
    frame["YEAR.1"] = frame["YEAR.1"].astype(int)
    frame["season"] = frame["YEAR"].map(normalize_flu_season_label)
    frame = frame.sort_values(["YEAR.1", "WEEK"], kind="mergesort").reset_index(drop=True)
    frame["t"] = range(len(frame))
    return frame


def filter_series(
    frame: pd.DataFrame,
    age_category: str = "Overall",
    catchment: str = "Entire Network",
    sex_category: str = "Overall",
    race_category: str = "Overall",
    virus_category: str = "Overall",
    seasons: Iterable[str] | None = None,
    series_name: str | None = None,
) -> pd.DataFrame:
    """Filter to one benchmark series and rebuild a continuous weekly index."""
    mask = (
        (frame["CATCHMENT"] == catchment)
        & (frame["AGE CATEGORY"] == age_category)
        & (frame["SEX CATEGORY"] == sex_category)
        & (frame["RACE CATEGORY"] == race_category)
        & (frame["VIRUS TYPE CATEGORY"] == virus_category)
        & _season_mask(frame, seasons)
    )
    series = frame.loc[mask].copy()
    series = series.dropna(subset=["WEEKLY RATE"]).copy()
    series = series.sort_values(["YEAR.1", "WEEK"], kind="mergesort").reset_index(drop=True)
    series["t"] = range(len(series))
    series["series_name"] = series_name or age_category
    return series


def build_flu_series_frames(
    frame: pd.DataFrame,
    include_age_groups: bool,
    age_groups: Iterable[str],
    seasons: Iterable[str] | None = None,
    season_mode: str = SEASON_MODE_POOLED,
) -> list[dict[str, object]]:
    """Build benchmark series frames with optional multi-season scoping.

    Pooled multi-season mode concatenates seasons into a single sequence. That is useful for
    smoke/descriptive runs, but paper-level claims should use separate seasons or an explicit
    season-level train/validation/test split.
    """
    mode = _validate_season_mode(season_mode)
    age_categories = ["Overall", *list(age_groups)] if include_age_groups else ["Overall"]
    requested_seasons = _normalize_requested_seasons(seasons)
    selected_seasons = list(requested_seasons) if requested_seasons else available_flu_seasons(frame)

    series_frames: list[dict[str, object]] = []
    if mode == SEASON_MODE_POOLED:
        if len(selected_seasons) > 1:
            warnings.warn(POOLED_MULTI_SEASON_WARNING, UserWarning, stacklevel=2)
        for age_category in age_categories:
            series_frames.append(
                {
                    "series_name": age_category,
                    "age_category": age_category,
                    "seasons": tuple(selected_seasons),
                    "is_robustness": age_category != "Overall",
                    "frame": filter_series(frame, age_category=age_category, seasons=selected_seasons),
                }
            )
        return series_frames

    for season in selected_seasons:
        for age_category in age_categories:
            series_frames.append(
                {
                    "series_name": format_flu_series_name(age_category, season),
                    "age_category": age_category,
                    "seasons": (season,),
                    "is_robustness": age_category != "Overall",
                    "frame": filter_series(
                        frame,
                        age_category=age_category,
                        seasons=[season],
                        series_name=format_flu_series_name(age_category, season),
                    ),
                }
            )
    return series_frames


def build_processed_series(
    frame: pd.DataFrame,
    include_age_groups: bool,
    age_groups: Iterable[str],
    seasons: Iterable[str] | None = None,
    season_mode: str = SEASON_MODE_POOLED,
) -> pd.DataFrame:
    """Build the primary series and optional robustness slices in one table."""
    series_frames = [
        item["frame"]
        for item in build_flu_series_frames(
            frame=frame,
            include_age_groups=include_age_groups,
            age_groups=age_groups,
            seasons=seasons,
            season_mode=season_mode,
        )
    ]
    combined = pd.concat(series_frames, ignore_index=True)
    columns = [
        "series_name",
        "season",
        "YEAR",
        "YEAR.1",
        "WEEK",
        "t",
        "CATCHMENT",
        "AGE CATEGORY",
        "SEX CATEGORY",
        "RACE CATEGORY",
        "VIRUS TYPE CATEGORY",
        "WEEKLY RATE",
        "CUMULATIVE RATE",
    ]
    return combined.loc[:, columns]


def save_processed_outputs(
    processed: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Persist the benchmark-ready processed tables."""
    output_dir.mkdir(parents=True, exist_ok=True)
    processed.to_csv(output_dir / "flusurv_benchmark_series.csv", index=False)
    overall = processed.loc[processed["AGE CATEGORY"] == "Overall"].copy()
    overall.to_csv(output_dir / "flusurv_primary_overall.csv", index=False)
