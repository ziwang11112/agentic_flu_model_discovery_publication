from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChronologicalSplit:
    """Chronological train/validation/test partition."""

    train_end: int
    val_end: int
    n_obs: int

    @property
    def train_slice(self) -> slice:
        return slice(0, self.train_end)

    @property
    def val_slice(self) -> slice:
        return slice(self.train_end, self.val_end)

    @property
    def test_slice(self) -> slice:
        return slice(self.val_end, self.n_obs)


def make_chronological_split(
    n_obs: int,
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
) -> ChronologicalSplit:
    """Split a univariate series chronologically."""
    train_end = max(1, int(n_obs * train_fraction))
    val_end = max(train_end + 1, int(n_obs * (train_fraction + val_fraction)))
    val_end = min(val_end, n_obs - 1)
    return ChronologicalSplit(train_end=train_end, val_end=val_end, n_obs=n_obs)
