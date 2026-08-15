"""Regression tests for the memory-efficient LLP event graph.

The optimized EventGraph must remain numerically and structurally equivalent to
SET-ANUBIS' historical per-particle dictionary implementation.
"""

from __future__ import annotations

import ast
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from SetAnubis.core.Selection.domain.LLPAnalyzer import EventGraph, LLPAnalyzer, Schema


class _LegacyEventGraph:
    """Historical EventGraph implementation kept only as a test oracle."""

    def __init__(self, df: pd.DataFrame) -> None:
        Schema.ensure(df)
        self.df = df
        self._row_index: Dict[Tuple[int, int], int] = {
            (int(ev), int(pidx)): int(i)
            for i, ev, pidx in zip(
                df.index,
                df["eventNumber"].to_list(),
                df["particleIndex"].to_list(),
            )
        }

        def _to_list(value) -> List[int]:
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    parsed = ast.literal_eval(value)
                    return parsed if isinstance(parsed, list) else []
                except Exception:
                    return []
            return []

        children_series = df["childrenIndices"].apply(_to_list)
        self._children = {
            (int(ev), int(pidx)): list(children)
            for ev, pidx, children in zip(
                df["eventNumber"].to_list(),
                df["particleIndex"].to_list(),
                children_series.to_list(),
            )
        }
        self._pid = {
            (int(ev), int(pidx)): int(pid)
            for ev, pidx, pid in zip(
                df["eventNumber"].to_list(),
                df["particleIndex"].to_list(),
                df["PID"].to_list(),
            )
        }
        self._nchildren = {
            (int(ev), int(pidx)): int(nc) if not pd.isna(nc) else 0
            for ev, pidx, nc in zip(
                df["eventNumber"].to_list(),
                df["particleIndex"].to_list(),
                df["nChildren"].to_list(),
            )
        }

    def row_of(self, event: int, pidx: int) -> Optional[int]:
        return self._row_index.get((int(event), int(pidx)))

    def children_of(self, event: int, pidx: int) -> List[int]:
        return self._children.get((int(event), int(pidx)), [])

    def pid_of(self, event: int, pidx: int) -> int:
        return self._pid.get((int(event), int(pidx)), 0)

    def nchildren_of(self, event: int, pidx: int) -> int:
        return self._nchildren.get((int(event), int(pidx)), 0)


def _sample_df() -> pd.DataFrame:
    rows = []

    def add(
        event,
        particle_index,
        pid,
        status,
        nchildren,
        children,
        px,
        py,
        pt,
        charge,
        prod_dist,
        pz=0.0,
        energy=1.0,
    ):
        rows.append(
            {
                "eventNumber": event,
                "particleIndex": particle_index,
                "px": px,
                "py": py,
                "pz": pz,
                "E": energy,
                "pt": pt,
                "status": status,
                "PID": pid,
                "charge": charge,
                "nChildren": nchildren,
                "childrenIndices": children,
                "prodVertexDist": prod_dist,
                "weight": 1.25,
            }
        )

    # Event 1 includes the special identical LLP -> LLP transport chain.
    add(1, 0, 9900012, 2, 1, [1], 1, 2, np.hypot(1, 2), 0, 0)
    add(1, 1, 9900012, 2, 3, "[2, 3, 4]", 1, 2, np.hypot(1, 2), 0, 50)
    add(1, 2, 11, 1, 0, [], 3, 4, 5, -1, 50, pz=1, energy=6)
    add(1, 3, -11, 1, 0, "[]", -3, 1, np.hypot(3, 1), 1, 50, pz=-1, energy=5)
    add(1, 4, 12, 1, 0, [], 2, -2, np.hypot(2, 2), 0, 50, energy=3)
    add(1, 5, 211, 1, 0, [], 5, 0, 5, 1, 1, pz=2, energy=6)
    add(1, 6, 111, 1, 0, [], 0, 4, 4, 0, 2, pz=1, energy=5)

    # Event 2 contains a stable LLP plus ordinary prompt final states.
    add(2, 0, 9900012, 1, 0, [], 2, 0, 2, 0, 0)
    add(2, 1, 13, 1, 0, [], 1, 1, np.hypot(1, 1), -1, 1, energy=2)
    add(2, 2, 14, 1, 0, [], 3, 0, 3, 0, 1, energy=3)

    # Malformed childrenIndices checks the historical parsing fallback.
    add(3, 0, 211, 1, 0, "not-a-list", 1, 0, 1, 1, 1)

    df = pd.DataFrame(rows)
    df.index = np.arange(100, 100 + len(df))
    return df


def test_sample_dataframe_bundle_is_exactly_legacy_equivalent():
    df = _sample_df()
    cfg = {"chargedTrack": 0.5}

    legacy = LLPAnalyzer(df, cfg)
    legacy.graph = _LegacyEventGraph(legacy.df)
    expected = legacy.create_sample_dataframes(9900012)

    optimized = LLPAnalyzer(df, cfg)
    actual = optimized.create_sample_dataframes(9900012)

    assert actual.keys() == expected.keys()
    for key in expected:
        assert_frame_equal(
            actual[key],
            expected[key],
            check_exact=True,
            check_dtype=True,
            check_index_type=True,
            check_column_type=True,
        )


def test_event_graph_keeps_legacy_duplicate_key_semantics():
    df = _sample_df().iloc[:2].copy()
    df.loc[df.index[1], "eventNumber"] = int(df.iloc[0]["eventNumber"])
    df.loc[df.index[1], "particleIndex"] = int(df.iloc[0]["particleIndex"])

    old = _LegacyEventGraph(df)
    new = EventGraph(df)

    for method in ("row_of", "children_of", "pid_of", "nchildren_of"):
        assert getattr(new, method)(1, 0) == getattr(old, method)(1, 0)


def test_analyzer_no_longer_duplicates_the_full_input_dataframe():
    df = _sample_df()
    analyzer = LLPAnalyzer(df, {"chargedTrack": 0.5})

    assert analyzer.df is df
    assert not hasattr(analyzer.graph, "_row_index")
    assert not hasattr(analyzer.graph, "_children")
    assert not hasattr(analyzer.graph, "_pid")
    assert not hasattr(analyzer.graph, "_nchildren")
