from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
import types

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

if importlib.util.find_spec("particle") is None:
    particle = types.ModuleType("particle")
    particle.__spec__ = importlib.machinery.ModuleSpec("particle", loader=None)
    sys.modules["particle"] = particle

# Optional JetBuilder dependencies are stubbed because this test injects its
# own deterministic createJetDF implementation.
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

from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource, SourceConfig
from SetAnubis.core.Selection.domain.HepMCFrameBuilder import HepmcFrameBuilder, HepmcFrameOptions
from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer
from SetAnubis.core.Selection.domain.isolation import IsolationComputer
import SetAnubis.core.Selection.domain.JetBuilder as jet_mod


class _Pos:
    def __init__(self, x, y, z, t=0.0):
        self.x, self.y, self.z, self.t = x, y, z, t


class _Vertex:
    def __init__(self, x, y, z, t=0.0):
        self.position = _Pos(x, y, z, t)


class _Particle:
    def __init__(self, idx, pid, status, p4, prod, end=None, mass=0.0):
        self.id = idx
        self.pid = pid
        self.status = status
        self.momentum = p4
        self.generated_mass = mass
        self.production_vertex = prod
        self.end_vertex = end
        self.parents = []
        self.children = []


class _Event:
    def __init__(self, particles, weight):
        self.particles = particles
        self.weights = [weight]


class _Neo:
    _charges = {9900012: 0.0, 11: -1.0, -11: 1.0, 211: 1.0, 22: 0.0}

    def get_particle(self, pid):
        return {"charge": self._charges.get(int(pid), 0.0)}


def _events(n=5):
    out = []
    for ev in range(n):
        prod = _Vertex(0.0, 0.0, 0.0)
        decay = _Vertex(100.0 + ev, 20.0, 300.0)
        n1 = _Particle(1, 9900012, 2, (10.0, 2.0, 30.0, 32.0), prod, decay, 1.0)
        em = _Particle(2, 11, 1, (2.0, 1.0, 3.0, 4.0), decay)
        ep = _Particle(3, -11, 1, (-1.0, 1.5, 2.0, 3.0), decay)
        prompt = _Particle(4, 211, 1, (20.0 + ev, 1.0, 2.0, 22.0 + ev), prod)
        photon = _Particle(5, 22, 1, (3.0, 4.0, 1.0, 6.0), prod)
        n1.children = [em, ep]
        em.parents = [n1]
        ep.parents = [n1]
        out.append(_Event([n1, em, ep, prompt, photon], 1.0 + ev / 10.0))
    return out


def _fake_create_jet_df(event_numbers, charged, neutral):
    # Deterministic event-local jet table; enough to exercise isolation and
    # verify that chunking preserves global event identifiers/order.
    rows = []
    for ev in event_numbers:
        rows.append(
            {
                "eventNumber": int(ev),
                "p": 50.0,
                "pt": 40.0,
                "px": 40.0,
                "py": 0.0,
                "pz": 30.0,
                "E": 55.0,
                "eta": 0.2,
                "phi": 0.1,
                "weight": 1.0,
            }
        )
    return pd.DataFrame(rows)


class _Thresholds:
    jet = 15.0
    chargedTrack = 5.0


class _Selection:
    minPt = _Thresholds()
    minP = _Thresholds()


def test_chunked_preprocessing_matches_one_shot_compact_bundle(monkeypatch):
    events = _events(5)
    neo = _Neo()
    pt_cfg = {"chargedTrack": 5.0, "neutralTrack": 5.0, "jet": 15.0}

    monkeypatch.setattr(jet_mod, "createJetDF", _fake_create_jet_df)

    # One-shot reference using the same compact preprocessing operations.
    builder = HepmcFrameBuilder(neo, options=HepmcFrameOptions(progress_every=None))
    full_df, _ = builder.build_from_events(events)
    analyzer = LLPAnalyzer(full_df, pt_cfg)
    reference = analyzer.create_selection_working_set(9900012)
    cfs = reference["chargedFinalStates"]
    nfs = reference["neutralFinalStates"]
    ev = np.unique(
        np.concatenate(
            [
                cfs["eventNumber"].to_numpy(dtype=int, copy=False),
                nfs["eventNumber"].to_numpy(dtype=int, copy=False),
            ]
        )
    )
    reference["finalStatePromptJets"] = _fake_create_jet_df(ev, cfs, nfs)
    reference["LLPs"] = IsolationComputer(_Selection()).attach_min_delta_r(reference)
    reference = {"LLPs": reference["LLPs"], "LLPchildren": reference["LLPchildren"]}

    # Fake pyhepmc.open used by the native chunked source.
    pyhepmc = types.ModuleType("pyhepmc")

    class _Open:
        def __enter__(self):
            return iter(events)
        def __exit__(self, exc_type, exc, tb):
            return False

    pyhepmc.open = lambda _path: _Open()
    monkeypatch.setitem(sys.modules, "pyhepmc", pyhepmc)

    source = EventsBundleSource.from_hepmc_native(
        ["fake.hepmc"],
        neo_manager=neo,
        cfg=SourceConfig(llp_pid=9900012, pt_min_cfg=pt_cfg),
        frame_options={"progress_every": None},
        chunk_size=2,
        max_events=5,
    )
    actual = source.materialize_selection_ready_chunked(_Selection())

    assert list(actual) == ["LLPs", "LLPchildren"]
    assert_frame_equal(actual["LLPs"], reference["LLPs"], check_exact=True, check_dtype=True)
    assert_frame_equal(
        actual["LLPchildren"], reference["LLPchildren"], check_exact=True, check_dtype=True
    )
