import pytest
from SetAnubis.core.ModelCore.domain.SetAnubisManager import (
    SetAnubisManager,
    SetAnubisPortsConfig,
)


class FakeNode:
    def __init__(self, value=None, deps=None, expr=None, block="BLOCK", code=1):
        self.value = value
        self.dependencies = list(deps or [])
        self.expression = expr
        self.lha_block = block
        self.lha_code = code

class FakeExpressionTree:
    def __init__(self, a=1.0, b=2.0):
        self.nodes = {
            "a": FakeNode(value=a, deps=[], expr=None, block="INPUTS", code=1),
            "b": FakeNode(value=b, deps=[], expr=None, block="INPUTS", code=2),
            "sum_ab": FakeNode(value=None, deps=["a", "b"], expr="a + b", block="CALC", code=42),
        }

    def copy(self):
        new = FakeExpressionTree()
        new.nodes = {
            k: FakeNode(n.value, list(n.dependencies), n.expression, n.lha_block, n.lha_code)
            for k, n in self.nodes.items()
        }
        return new

    def evaluate_partial(self, names):
        if "sum_ab" in self.nodes:
            a = self.nodes["a"].value
            b = self.nodes["b"].value
            self.nodes["sum_ab"].value = a + b

    def get_value(self, name):
        return self.nodes[name]

    def get_remaining_leaves(self):
        return [k for k, v in self.nodes.items() if not v.dependencies]

class FakeUFOGetterPort:
    def __init__(self, tree=None):
        self._tree = tree or FakeExpressionTree()

    def get(self):
        return self._tree

class FakeParticlesProxy:
    def __init__(self, base):
        self._base = dict(base)

    def get_all_particles(self):
        return dict(self._base)


BASE_PARTICLES = {
    11: {
        "name": "e-",
        "antiname": "e+",
        "pdg_code": 11,
        "charge": -1,
        "spin": 2,
        "mass": complex(0.000511),  # GeV
    },
    24: {
        "name": "W+",
        "antiname": "W-",
        "pdg_code": 24,
        "charge": +1,
        "spin": 3,
        "mass": complex(80.379),  # GeV
    },
}


@pytest.fixture
def manager():
    ports = SetAnubisPortsConfig(
        UFO_getter=FakeUFOGetterPort(),
        particle_from_json=FakeParticlesProxy(BASE_PARTICLES),
    )
    base_particles_list = list(BASE_PARTICLES.values())
    return SetAnubisManager(ports, base_particles_list)


def test_evaluate_all_parameters(manager):
    params = manager.get_all_parameters()
    assert isinstance(params, dict)
    assert "a" in params and "b" in params and "sum_ab" in params
    assert params["sum_ab"]["value"] == complex(1.0 + 2.0)

def test_set_leaf_parameter_value_updates_tree(manager):
    manager.set_leaf_parameter_value("a", 10.0)
    params = manager.get_all_parameters()
    assert params["a"]["value"] == complex(10.0)
    assert params["sum_ab"]["value"] == complex(10.0 + 2.0)

def test_get_leaf_parameters(manager):
    leaves = manager.get_leaf_parameters()
    assert set(leaves.keys()) == {"a", "b"}
    assert leaves["a"] == 1.0
    assert leaves["b"] == 2.0

def test_get_parameter_expr_returns_node(manager):
    node = manager.get_parameter_expr("sum_ab")
    assert node.expression == "a + b"
    assert node.dependencies == ["a", "b"]

def test_get_particle_known(manager):
    p = manager.get_particle(11)
    print("ppasbar : ", p)
    print("bah quoi : ", p["charge"] != -1)
    assert p["pdg_code"] == 11
    assert p["charge"] == -1
    assert "mass" in p

def test_get_particle_charge_sign_flip(manager):
    pbar = manager.get_particle(-11)
    print("pbar : ", pbar)
    assert pbar["pdg_code"] == -11
    assert pbar["charge"] == 1
