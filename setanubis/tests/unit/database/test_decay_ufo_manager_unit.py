import math
import types
import pytest

import SetAnubis.core.DataBase.domain.UFODecayManager as decay_mod



class _Node:
    def __init__(self, name, value):
        self.name = name
        self.value = value

class FakeSMTree:
    def __init__(self, mapping):
        self.nodes = {k: _Node(k, v) for k, v in mapping.items()}

class FakeUFOManager:
    """
    Fournit des décays et des paramètres SM contrôlés.
    """
    def __init__(self, path):
        self._path = path
        self._decays = {
            4000: {
                (1000, 2000): "a + b",
                (2000, 3000): "cos(MZ) + k",
                (3000, 1000): "theta + 1",
            },
            5000: {
                (2000, 1000): "2*a + 1",
            },
        }
        self._decays_from_new = {
            4000: {(1000, 2000): "a + b"},
            5000: {(2000, 1000): "2*a + 1"},
        }
        self._decays_to_new = {
            4000: {(2000, 3000): "cos(MZ) + k"},
        }
        self._new_particles = [
            {"name": "X", "pdg_code": 4000},
            {"name": "Y", "pdg_code": 5000},
        ]
        self._sm_tree = FakeSMTree({"a": 3.0, "b": 5.0, "MZ": 2.0, "k": 7.0})

    def get_decays_from_new_particles(self):
        return self._decays_from_new

    def get_decays_to_new_particles(self):
        return self._decays_to_new

    def get_new_particles(self):
        return self._new_particles

    def get_decays(self):
        return {m: dict(ch) for m, ch in self._decays.items()}

    def get_sm_param_tree_evaluated(self):
        return self._sm_tree


@pytest.fixture(autouse=True)
def patch_ufo_manager(monkeypatch):
    monkeypatch.setattr(decay_mod, "UFOManager", FakeUFOManager, raising=True)


def test_init_collects_and_flattens_lists():
    mgr = decay_mod.DecayUFOManager()
    assert isinstance(mgr.decay_from_new_particles, list)
    assert isinstance(mgr.decay_to_new_particles, list)
    assert (1000, 2000) in {c for group in mgr.decay_from_new_particles for c in group}
    assert (2000, 3000) in {c for group in mgr.decay_to_new_particles for c in group}
    assert 4000 in mgr.decays and (1000, 2000) in mgr.decays[4000]


def test_evaluate_with_sm_substitutes_and_simplifies():
    mgr = decay_mod.DecayUFOManager()
    mgr.evaluate_with_sm()

    expr_1 = mgr.decays[4000][(1000, 2000)]
    import sympy as sp
    val_1 = float(sp.N(sp.sympify(expr_1)))
    assert val_1 == pytest.approx(8.0, rel=1e-12)

    expr_2 = mgr.decays[4000][(2000, 3000)]
    val_2 = float(sp.N(sp.sympify(expr_2)))
    assert val_2 == pytest.approx(math.cos(2.0) + 7.0, rel=1e-12)

    expr_3 = mgr.decays[4000][(3000, 1000)]
    assert "theta" in expr_3


def test_create_func_caches_and_evaluate():
    mgr = decay_mod.DecayUFOManager()
    mgr.evaluate_with_sm()
    mgr.create_func_caches()

    f = mgr.get_function(4000, (3000, 1000))
    assert callable(f)
    out = mgr.evaluate(4000, (3000, 1000), {"theta": 2.5})
    assert out == pytest.approx(3.5, rel=1e-12)

    f2 = mgr.get_function(4000, (1000, 2000))
    out2 = f2({})
    assert out2 == pytest.approx(8.0, rel=1e-12)

    funcs, params = mgr.get_caches()
    assert 4000 in funcs and (3000, 1000) in funcs[4000]
    assert params[4000][(3000, 1000)] == ["theta"]
