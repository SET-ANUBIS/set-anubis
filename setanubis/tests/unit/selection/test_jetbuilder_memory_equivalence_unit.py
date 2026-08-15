"""Exact-output regression tests for the compact JetDFBuilder event index."""

from __future__ import annotations

import importlib.util
import importlib.machinery
import sys
import types

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

# Keep this unit test runnable without optional native FastJet wheels.  The
# clustering backend is injected below, so only ak.to_numpy is required.
if importlib.util.find_spec("awkward") is None:
    awkward = types.ModuleType("awkward")
    awkward.__spec__ = importlib.machinery.ModuleSpec("awkward", loader=None)
    awkward.from_numpy = lambda value: value
    awkward.to_numpy = np.asarray
    sys.modules["awkward"] = awkward
if importlib.util.find_spec("fastjet") is None:
    fastjet = types.ModuleType("fastjet")
    fastjet.__spec__ = importlib.machinery.ModuleSpec("fastjet", loader=None)
    fastjet.antikt_algorithm = 1
    fastjet.JetDefinition = lambda *args, **kwargs: object()
    fastjet._pyjet = types.SimpleNamespace(AwkwardClusterSequence=object)
    fastjet.ClusterSequence = types.SimpleNamespace()
    sys.modules["fastjet"] = fastjet

import awkward as ak

from SetAnubis.core.Selection.domain.JetBuilder import JetDFBuilder, _p, _pt


class _Jets:
    def __init__(self, px, py, pz, energy):
        self._data = {
            "px": np.asarray(px, dtype=float),
            "py": np.asarray(py, dtype=float),
            "pz": np.asarray(pz, dtype=float),
            "E": np.asarray(energy, dtype=float),
        }

    def __len__(self):
        return len(self._data["px"])

    def __getitem__(self, key):
        return self._data[key]


class _DeterministicClustering:
    """Small backend sensitive to the exact particle input ordering."""

    def __init__(self):
        self.calls = []

    def cluster_event(self, px, py, pz, energy):
        self.calls.append(tuple(arr.copy() for arr in (px, py, pz, energy)))
        if len(px) == 1:
            return _Jets([px[0]], [py[0]], [pz[0]], [energy[0]])
        return _Jets(
            [px[0], px[1:].sum()],
            [py[0], py[1:].sum()],
            [pz[0], pz[1:].sum()],
            [energy[0], energy[1:].sum()],
        )


def _legacy_build(builder, event_numbers, charged, neutral):
    """Historical pandas-groupby implementation used as the test oracle."""
    c_groups = builder._group_by_event(charged)
    n_groups = builder._group_by_event(neutral)

    out_event, out_p, out_pt = [], [], []
    out_px, out_py, out_pz, out_E = [], [], [], []
    out_eta, out_phi, out_weight = [], [], []

    for event in event_numbers:
        event = int(event)
        cdf = c_groups.get(event)
        ndf = n_groups.get(event)

        if (cdf is None or cdf.empty) and (ndf is None or ndf.empty):
            continue

        if cdf is None or cdf.empty:
            px = ndf["px"].to_numpy(dtype=float, copy=False)
            py = ndf["py"].to_numpy(dtype=float, copy=False)
            pz = ndf["pz"].to_numpy(dtype=float, copy=False)
            energy = ndf["E"].to_numpy(dtype=float, copy=False)
        elif ndf is None or ndf.empty:
            px = cdf["px"].to_numpy(dtype=float, copy=False)
            py = cdf["py"].to_numpy(dtype=float, copy=False)
            pz = cdf["pz"].to_numpy(dtype=float, copy=False)
            energy = cdf["E"].to_numpy(dtype=float, copy=False)
        else:
            px = np.concatenate([cdf["px"].to_numpy(dtype=float, copy=False), ndf["px"].to_numpy(dtype=float, copy=False)])
            py = np.concatenate([cdf["py"].to_numpy(dtype=float, copy=False), ndf["py"].to_numpy(dtype=float, copy=False)])
            pz = np.concatenate([cdf["pz"].to_numpy(dtype=float, copy=False), ndf["pz"].to_numpy(dtype=float, copy=False)])
            energy = np.concatenate([cdf["E"].to_numpy(dtype=float, copy=False), ndf["E"].to_numpy(dtype=float, copy=False)])

        if px.size == 0:
            continue

        jets = builder.clustering.cluster_event(px, py, pz, energy)
        if len(jets) == 0:
            continue

        weight = builder._event_weight(cdf, ndf)
        jpx = ak.to_numpy(jets["px"])
        jpy = ak.to_numpy(jets["py"])
        jpz = ak.to_numpy(jets["pz"])
        jE = ak.to_numpy(jets["E"])
        _, jeta, jphi = builder._JetDFBuilder__to_spherical_vec(jpx, jpy, jpz)
        jpt = _pt(jpx, jpy)
        jp = _p(jpx, jpy, jpz)

        out_event.extend([event] * len(jets))
        out_p.extend(jp.tolist())
        out_pt.extend(jpt.tolist())
        out_px.extend(jpx.tolist())
        out_py.extend(jpy.tolist())
        out_pz.extend(jpz.tolist())
        out_E.extend(jE.tolist())
        out_eta.extend(jeta.tolist())
        out_phi.extend(jphi.tolist())
        out_weight.extend([weight] * len(jets))

    return pd.DataFrame(
        {
            "eventNumber": out_event,
            "p": out_p,
            "pt": out_pt,
            "px": out_px,
            "py": out_py,
            "pz": out_pz,
            "E": out_E,
            "eta": out_eta,
            "phi": out_phi,
            "weight": out_weight,
        }
    )


def test_compact_event_index_preserves_exact_legacy_jet_inputs_and_output():
    charged = pd.DataFrame(
        {
            "eventNumber": [2, 1, 2, 1, 4],
            "px": [20.0, 1.0, 21.0, 2.0, 40.0],
            "py": [0.0, 3.0, 1.0, 4.0, 2.0],
            "pz": [2.0, 5.0, 3.0, 6.0, 4.0],
            "E": [21.0, 6.0, 22.0, 7.0, 41.0],
            "weight": [2.2, 1.1, 2.2, 1.1, 4.4],
        }
    )
    neutral = pd.DataFrame(
        {
            "eventNumber": [1, 3, 2, 1],
            "px": [10.0, 30.0, 11.0, 12.0],
            "py": [7.0, 8.0, 9.0, 10.0],
            "pz": [11.0, 31.0, 12.0, 13.0],
            "E": [16.0, 44.0, 18.0, 20.0],
            "weight": [1.1, 3.3, 2.2, 1.1],
        }
    )
    events = [1, 2, 3, 4, 5]

    legacy_clustering = _DeterministicClustering()
    optimized_clustering = _DeterministicClustering()
    legacy_builder = JetDFBuilder(legacy_clustering)
    optimized_builder = JetDFBuilder(optimized_clustering)

    expected = _legacy_build(legacy_builder, events, charged, neutral)
    actual = optimized_builder.build(events, charged, neutral)

    assert_frame_equal(actual, expected, check_exact=True, check_dtype=True)
    assert len(legacy_clustering.calls) == len(optimized_clustering.calls)
    for old_call, new_call in zip(legacy_clustering.calls, optimized_clustering.calls):
        for old_array, new_array in zip(old_call, new_call):
            np.testing.assert_array_equal(new_array, old_array)
