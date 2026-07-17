"""Unit tests for event-wise azimuthal folding."""

from __future__ import annotations

import math

import pandas as pd

from SetAnubis.core.Selection.domain.PhiFoldTransform import (
    _flip_xy_vertex,
    _parse_fourvec,
    phi_fold_df,
)


def test_four_vector_parsing_and_vertex_flip():
    assert _parse_fourvec([1, 2, 3, 4]) == (1, 2, 3, 4)
    assert _parse_fourvec("(1, 2, 3, 4)") == (1, 2, 3, 4)
    assert _parse_fourvec("not-a-vector") == "not-a-vector"
    assert _flip_xy_vertex((1, 2, 3, 4)) == (-1.0, -2.0, 3.0, 4.0)
    assert _flip_xy_vertex((-1, -1, -1, -1)) == (-1, -1, -1, -1)
    assert _flip_xy_vertex(None) is None


def test_phi_fold_flips_all_particles_in_selected_events_only():
    frame = pd.DataFrame(
        {
            "eventNumber": [1, 1, 2],
            "PID": [9900012, 11, 9900012],
            "phi": [-0.5, 0.2, 0.4],
            "px": [1.0, 2.0, 3.0],
            "py": [4.0, 5.0, 6.0],
            "prodVertex": ["(1, 2, 3, 4)", (2, 3, 4, 5), (3, 4, 5, 6)],
            "decayVertex": [(-1, -1, -1, -1), [1, 1, 1, 1], None],
        }
    )

    folded = phi_fold_df(frame, llp_pid=9900012)

    assert folded is not frame
    assert folded.loc[0, "px"] == -1.0
    assert folded.loc[1, "px"] == -2.0
    assert folded.loc[2, "px"] == 3.0
    assert folded.loc[0, "py"] == -4.0
    assert math.isclose(folded.loc[0, "phi"], math.pi - 0.5)
    assert math.isclose(folded.loc[1, "phi"], 0.2 - math.pi)
    assert folded.loc[0, "prodVertex"] == (-1.0, -2.0, 3.0, 4.0)
    assert folded.loc[0, "decayVertex"] == (-1, -1, -1, -1)
    assert folded.loc[2, "prodVertex"] == (3, 4, 5, 6)


def test_phi_fold_returns_unchanged_copy_when_no_negative_llp_phi():
    frame = pd.DataFrame(
        {"eventNumber": [1], "PID": [9900012], "phi": [0.5], "px": [1.0], "py": [2.0]}
    )
    result = phi_fold_df(frame, llp_pid=9900012)
    pd.testing.assert_frame_equal(result, frame)
    assert result is not frame
