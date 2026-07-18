"""Dependency-light helpers shared by the HepMC dashboard callbacks."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd


def sampled_overlay_event_ids(
    frame: pd.DataFrame,
    allowed_events: Iterable[Any] | None,
    max_events: Any,
) -> list[int]:
    """Return deterministic event identifiers for the decay-tree overlay.

    ``frame`` represents the particle rows that remain visible after the
    particle-level filters. ``allowed_events`` represents optional event-level
    restrictions; ``None`` means that no such restriction is active, not that
    no event is allowed.
    """
    if frame is None or frame.empty or "event" not in frame.columns:
        return []

    event_values = pd.to_numeric(frame["event"], errors="coerce").dropna()
    available = {int(value) for value in event_values.tolist()}

    if allowed_events is not None:
        normalised_allowed: set[int] = set()
        for value in allowed_events:
            try:
                normalised_allowed.add(int(value))
            except (TypeError, ValueError):
                continue
        available.intersection_update(normalised_allowed)

    try:
        limit = int(max_events)
    except (TypeError, ValueError):
        limit = 40

    if limit <= 0:
        return []
    return sorted(available)[:limit]
