import os
import types
import pytest

import SetAnubis.core.DataBase.domain.UFOManager as ufo_manager_mod
import SetAnubis.core.DataBase.adapters.UFOParser as ufo_parser_mod


class ExpressionTreeFake:
    def __init__(self, params):
        self.params = [dict(p) for p in params]
        self._leaves = None
    def evaluate_from_leaves(self, leaves):
        self._leaves = list(leaves); return self
    def get_subgraph_from_leaves(self, leaves):
        return ExpressionTreeFake(self.params)
    def visualize(self):
        class Dot:
            def render(self, *args, **kwargs): pass
        return Dot()
    def convert_tree_to_list(self):
        return [dict(p) for p in self.params]


@pytest.fixture(autouse=True)
def patch_expression_tree(monkeypatch):
    monkeypatch.setattr(ufo_manager_mod, "ExpressionTree", ExpressionTreeFake, raising=True)


def make_parser_stub(sm_particles, model_particles, params):
    def parse(path):
        lower = path.lower()
        if lower.endswith("particles.py"):
            if "sm_nlo" in lower or "/sm/" in lower or "\\sm\\" in lower:
                return sm_particles
            return model_particles
        if lower.endswith("parameters.py"):
            return params
        return []
    return parse


def test_decays_and_filters(tmp_path, monkeypatch):
    model_particles = [
        {"name": "A", "pdg_code": 1000},
        {"name": "B", "pdg_code": 2000},
        {"name": "C", "pdg_code": 3000},
        {"name": "X", "pdg_code": 4000},
    ]
    sm_particles = [
        {"name": "A", "pdg_code": 1000},
        {"name": "B", "pdg_code": 2000},
        {"name": "C", "pdg_code": 3000},
    ]
    params = [
        {"name":"aEWM1", "lhablock":"SMINPUTS", "lhacode":[1], "value":127.9},
        {"name":"Gf",    "lhablock":"SMINPUTS", "lhacode":[2], "value":1.166e-5},
        {"name":"MZ",    "lhablock":"MASS",     "lhacode":[23],"value":91.1876},
    ]

    monkeypatch.setattr(ufo_manager_mod, "UFOParser",
                        types.SimpleNamespace(parse=make_parser_stub(sm_particles, model_particles, params)), raising=True)

    model_dir = tmp_path / "MyModel"
    model_dir.mkdir(parents=True, exist_ok=True)

    dec_src = '''
class Obj: pass

WDEC = Decay(name='X', particle=Obj.X, partial_widths={
    (Obj.A, Obj.B): 'a + b',
    (Obj.B, Obj.C): 'cos(MZ)'
})
'''
    (model_dir / "decays.py").write_text(dec_src, encoding="utf-8")

    mgr = ufo_manager_mod.UFOManager(str(model_dir))
    monkeypatch.setattr(mgr, "sm", str(tmp_path / "SM_NLO"))

    decs = mgr.get_decays()
    assert 4000 in decs
    keys = sorted(decs[4000].keys())
    assert keys == [(1000,2000), (2000,3000)]
    assert decs[4000][(1000,2000)] == "a + b"
    assert "cos(" in decs[4000][(2000,3000)]

    only_new = mgr.get_decays_from_new_particles()
    assert set(only_new.keys()) == {4000}

    (model_dir / "decays.py").write_text('''
class Obj: pass
WDEC = Decay(name='X', particle=Obj.X, partial_widths={
    (Obj.A, Obj.Y): 'kappa',
})
''', encoding="utf-8")

    model_particles.append({"name":"Y", "pdg_code": 5000})

    dec_to_new = mgr.get_decays_to_new_particles()
    assert 4000 in dec_to_new and (1000,5000) in dec_to_new[4000]
    assert dec_to_new[4000][(1000,5000)] == "kappa"


def test_param_tree_and_sm_evaluation(tmp_path, monkeypatch):
    model_particles = []
    sm_particles = []
    params = [
        {"name":"aEWM1", "lhablock":"SMINPUTS", "lhacode":[1], "value":127.9},
        {"name":"Gf",    "lhablock":"SMINPUTS", "lhacode":[2], "value":1.166e-5},
        {"name":"MZ",    "lhablock":"MASS",     "lhacode":[23],"value":91.1876},
        {"name":"alphaS","lhablock":"SMINPUTS", "lhacode":[3], "value":"1.0/log(MZ)"},
        {"name":"X",     "lhablock":"NEWB",     "lhacode":[1], "value":"aEWM1+Gf"},
    ]
    monkeypatch.setattr(ufo_manager_mod, "UFOParser",
                        types.SimpleNamespace(parse=make_parser_stub(sm_particles, model_particles, params)), raising=True)

    mgr = ufo_manager_mod.UFOManager(str(tmp_path))
    tree = mgr.get_param_tree()
    evald = mgr.evaluate_tree_from_sm_params(tree)
    lst = mgr.get_param_with_sm_evaluation()
    assert isinstance(lst, list) and len(lst) == len(params)
