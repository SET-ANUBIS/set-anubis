import os
import types
import pytest

import SetAnubis.core.DataBase.domain.UFOManager as ufo_manager_mod
import SetAnubis.core.DataBase.adapters.UFOParser as ufo_parser_mod



class DotFake:
    def __init__(self, state):
        self.state = state
    def render(self, filename, format="png", view=False):
        self.state["render_calls"].append((filename, format, view))

class ExpressionTreeFake:
    """
    Fake d'ExpressionTree correspondant à l'API utilisée par UFOManager :
      - constructeur(params)
      - evaluate_from_leaves(list[str]) -> self
      - get_subgraph_from_leaves(list[str]) -> nouveau ExpressionTreeFake
      - visualize() -> obj avec .render(...)
      - convert_tree_to_list() -> list[dict]
    """
    def __init__(self, params):
        self.params = [dict(p) for p in params]
        self.state = {"evaluated_with": None, "render_calls": []}

    def evaluate_from_leaves(self, leaves):
        self.state["evaluated_with"] = list(leaves)
        return self

    def get_subgraph_from_leaves(self, leaves):
        keep = set(leaves)
        changed = True
        while changed:
            changed = False
            for p in self.params:
                if p["name"] in keep:
                    continue
                v = p.get("value")
                if isinstance(v, str):
                    names = {w for w in v.replace("*", " ").replace("+", " ").replace("-", " ").replace("/", " ").split() if w.isidentifier()}
                    if names and names.issubset(keep):
                        keep.add(p["name"]); changed = True
        sub = [p for p in self.params if p["name"] in keep]
        return ExpressionTreeFake(sub)

    def visualize(self):
        return DotFake(self.state)

    def convert_tree_to_list(self):
        return [dict(p) for p in self.params]


@pytest.fixture(autouse=True)
def patch_expression_tree(monkeypatch):
    monkeypatch.setattr(ufo_manager_mod, "ExpressionTree", ExpressionTreeFake, raising=True)


def make_parser_stub(sm_particles, model_particles, params):
    """
    Fabrique un parse(path) qui renvoie des dicts selon le fichier demandé.
    - .../particles.py -> renvoie sm or model selon si 'SM_NLO' (ou '/sm/') apparaît dans le chemin
    - .../parameters.py -> renvoie params
    """
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


def test_get_all_and_new_and_sm_particles(monkeypatch, tmp_path):
    sm_particles = [
        {"name": "e-", "pdg_code": 11, "antiname": "e+", "charge": -1, "color": 1, "spin": 2, "mass": "Me"},
        {"name": "u",  "pdg_code": 2,  "antiname": "u~", "charge": 2/3, "color": 3, "spin": 2, "mass": "Mu"},
    ]
    model_particles = sm_particles + [
        {"name": "N",  "pdg_code": 9900012, "antiname": "N~", "charge": 0, "color": 1, "spin": 2, "mass": "MN"},
    ]
    params = []

    monkeypatch.setattr(ufo_manager_mod, "UFOParser", types.SimpleNamespace(parse=make_parser_stub(sm_particles, model_particles, params)), raising=True)

    mgr = ufo_manager_mod.UFOManager("/tmp/dummy-model")

    all_min = mgr.get_all_particles(more_infos=False)
    assert {"name":"e-","pdg_code":11} in all_min and {"name":"N","pdg_code":9900012} in all_min

    all_full = mgr.get_all_particles(more_infos=True)
    someN = next(x for x in all_full if x["pdg_code"] == 9900012)
    assert someN["spin"] == 2 and someN["charge"] == 0

    monkeypatch.setattr(mgr, "sm", "/path/to/SM_NLO")
    sm = mgr.get_sm_particles(more_infos=True)
    assert len(sm) == 2 and all("spin" in x for x in sm)

    newp = mgr.get_new_particles(more_infos=True)
    assert len(newp) == 1 and newp[0]["pdg_code"] == 9900012


def test_get_params_and_sm_params_and_trees(monkeypatch):
    model_particles = []
    sm_particles = []
    params = [
        {"name":"aEWM1", "lhablock":"SMINPUTS", "lhacode":[1], "value": 127.9},
        {"name":"Gf",    "lhablock":"SMINPUTS", "lhacode":[2], "value": 1.166e-5},
        {"name":"MW",    "lhablock":"MASS",     "lhacode":[24], "value": 80.379},
        {"name":"MZ",    "lhablock":"MASS",     "lhacode":[23], "value": 91.1876},
        {"name":"alphaS","lhablock":"SMINPUTS", "lhacode":[3], "value": "1.0/log(MZ)"},
        {"name":"X",     "lhablock":"NEWBLOCK", "lhacode":[1], "value": 42.0},
    ]

    monkeypatch.setattr(ufo_manager_mod, "UFOParser",
                        types.SimpleNamespace(parse=make_parser_stub(sm_particles, model_particles, params)), raising=True)

    mgr = ufo_manager_mod.UFOManager("/tmp/model")

    got = mgr.get_params()
    assert {"name","block","pdgcode","value"}.issubset(got[0].keys())

    sm_only = mgr.get_sm_params()
    names = {p["name"] for p in sm_only}
    assert names == {"aEWM1","Gf","MW","MZ"}

    tree = mgr.get_param_tree()
    assert isinstance(tree, ExpressionTreeFake)
    assert [p["name"] for p in tree.params] == [p["name"] for p in got]

    tree2 = mgr.evaluate_tree_from_sm_params(tree)
    assert tree2.state["evaluated_with"] == ["aEWM1","Gf","MW","MZ"]

    sm_tree = mgr.get_sm_param_tree_evaluated()
    keep_names = {p["name"] for p in sm_tree.params}
    assert {"aEWM1","Gf","MW","MZ"}.issubset(keep_names)


def test_get_param_with_sm_evaluation_visualize_render(monkeypatch, tmp_path):
    params = [
        {"name":"aEWM1", "lhablock":"SMINPUTS", "lhacode":[1], "value": 127.9},
        {"name":"MZ",    "lhablock":"MASS",     "lhacode":[23], "value": 91.1876},
        {"name":"alphaS","lhablock":"SMINPUTS", "lhacode":[3],  "value": "1.0/log(MZ)"},
    ]
    monkeypatch.setattr(ufo_manager_mod, "UFOParser",
                        types.SimpleNamespace(parse=make_parser_stub([], [], params)), raising=True)

    mgr = ufo_manager_mod.UFOManager(str(tmp_path))
    tree_list = mgr.get_param_with_sm_evaluation()

    assert isinstance(tree_list, list) and all(isinstance(d, dict) for d in tree_list)
