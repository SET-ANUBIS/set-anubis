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

class FakeUFOManager2:
    def __init__(self, path):
        self._decays = {
            9000: {
                (1, 2): "g + h",    
                (2, 3): "cos(MZ) + eta",
            }
        }
        self._from_new = {9000: {(1, 2): "g + h"}}
        self._to_new =   {9000: {(2, 3): "cos(MZ) + eta"}}
        self._new = [{"name": "X9000", "pdg_code": 9000}]
        self._sm_tree = FakeSMTree({"g": 0.1, "h": 0.2, "MZ": 1.5})

    def get_decays_from_new_particles(self): return self._from_new
    def get_decays_to_new_particles(self):   return self._to_new
    def get_new_particles(self):             return self._new
    def get_decays(self):                    return {m: dict(ch) for m, ch in self._decays.items()}
    def get_sm_param_tree_evaluated(self):   return self._sm_tree


@pytest.fixture(autouse=True)
def patch_ufo_manager(monkeypatch):
    monkeypatch.setattr(decay_mod, "UFOManager", FakeUFOManager2, raising=True)


def test_full_flow_substitute_then_evaluate():
    mgr = decay_mod.DecayUFOManager()
    mgr.evaluate_with_sm()

    import sympy as sp
    v12 = float(sp.N(sp.sympify(mgr.decays[9000][(1, 2)])))
    assert v12 == pytest.approx(0.1 + 0.2, rel=1e-12)

    expr_23 = mgr.decays[9000][(2, 3)]
    assert "eta" in expr_23
    val_eta0 = float(sp.N(sp.sympify(expr_23).subs({"eta": 0.0})))
    assert val_eta0 == pytest.approx(math.cos(1.5), rel=1e-12)

    mgr.create_func_caches()
    out = mgr.evaluate(9000, (2, 3), {"eta": 1.0})
    assert out == pytest.approx(math.cos(1.5) + 1.0, rel=1e-12)
