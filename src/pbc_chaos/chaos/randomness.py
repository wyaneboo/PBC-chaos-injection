"""Deterministic random helpers for chaos injection."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Iterable, Sequence
from typing import TypeVar

T = TypeVar("T")


def stable_seed(*parts: object) -> int:
    """Create a stable integer seed from arbitrary seed parts."""
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def seeded_random(*parts: object) -> random.Random:
    """Create a `random.Random` instance seeded from stable parts."""
    return random.Random(stable_seed(*parts))


def clamp_probability(value: float) -> float:
    """Clamp a probability into the inclusive 0..1 range."""
    return max(0.0, min(1.0, float(value)))


def weighted_choice(rng: random.Random, items: Sequence[tuple[T, float]]) -> T:
    """Choose one item from `(value, weight)` pairs."""
    if not items:
        raise ValueError("weighted_choice requires at least one item.")

    total = sum(max(0.0, weight) for _, weight in items)
    if total <= 0:
        raise ValueError("weighted_choice requires at least one positive weight.")

    threshold = rng.uniform(0, total)
    cumulative = 0.0
    for item, weight in items:
        cumulative += max(0.0, weight)
        if threshold <= cumulative:
            return item

    return items[-1][0]


def stable_sample(rng: random.Random, values: Iterable[T], sample_size: int) -> tuple[T, ...]:
    """Sample from an iterable using a supplied deterministic RNG."""
    materialized = tuple(values)
    if sample_size <= 0:
        return ()
    return tuple(rng.sample(materialized, min(sample_size, len(materialized))))

