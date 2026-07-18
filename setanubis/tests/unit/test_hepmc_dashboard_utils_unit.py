from __future__ import annotations

import pandas as pd

from SetAnubis.HepMCGUI.dashboard_utils import sampled_overlay_event_ids


def test_overlay_uses_visible_events_without_event_filter() -> None:
    frame = pd.DataFrame({"event": [7, 3, 7, 5], "pid": [1, 2, 3, 4]})

    assert sampled_overlay_event_ids(frame, None, 10) == [3, 5, 7]


def test_overlay_intersects_visible_and_allowed_events() -> None:
    frame = pd.DataFrame({"event": [1, 2, 3, 4]})

    assert sampled_overlay_event_ids(frame, {2, 4, 8}, 10) == [2, 4]


def test_overlay_limit_is_deterministic() -> None:
    frame = pd.DataFrame({"event": [9, 2, 5, 1]})

    assert sampled_overlay_event_ids(frame, None, 2) == [1, 2]
