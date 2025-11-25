import pytest
from typing import Dict, Any
from SetAnubis.core.ModelCore.domain.SetAnubisManager import (
    SetAnubisManager,
    SetAnubisPortsConfig,
)
from SetAnubis.core.ModelCore.adapters.output.ParticlesFromJSONProxy import (
    ParticlesFromJSONProxy,
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

class FakeUFOGetterPort:
    def __init__(self, tree=None):
        self._tree = tree or FakeExpressionTree()

    def get(self):
        return self._tree

class MemoryExtractor:
    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def extract(self, json_path: str) -> Dict[str, Any]:
        return dict(self._payload)


BASE_PARTICLES = {
    11: {
        "name": "e-",
        "antiname": "e+",
        "pdg_code": 11,
        "charge": -1,
        "spin": 2,
        "mass": complex(0.000511),  # GeV (base)
    },
}

JSON_PAYLOAD = {
    "13": {
        "name": "mu-",
        "antiName": "mu+",
        "spin": 2,
        "charge": -1,
        "mass": 105.658,  # MeV si on met mass_scale=1e-3 => 0.105658 GeV
    },
    "11": {
        "name": "should_not_override",
        "antiName": "should_not_override",
        "spin": 2,
        "charge": -1,
        "mass": 999.0,
    },
}

@pytest.fixture
def manager():
    extractor = MemoryExtractor(JSON_PAYLOAD)
    proxy = ParticlesFromJSONProxy(
        base_particles=BASE_PARTICLES,
        extractor=extractor,
        json_path="ignored.json",
        mass_scale=1e-3,
        mass_as_complex=True,
    )
    ports = SetAnubisPortsConfig(
        UFO_getter=FakeUFOGetterPort(),
        particle_from_json=proxy,
    )
    return SetAnubisManager(ports, base_particles=list(BASE_PARTICLES.values()))

def test_particles_merge_and_scaling(manager):
    allp = manager.get_all_particles()
    assert 11 in allp and 13 in allp

    assert allp[11]["name"] == "e-"
    assert allp[11]["mass"] == complex(0.000511)

    mu = allp[13]
    assert mu["name"] == "mu-"
    assert mu["antiname"] == "mu+"
    assert mu["spin"] == 2
    assert mu["charge"] == -1
    assert isinstance(mu["mass"], complex)
    assert mu["mass"].real == pytest.approx(0.105658, rel=1e-9)

def test_manager_evaluates_tree_and_reads_mass(manager):
    params = manager.get_all_parameters()
    assert params["sum_ab"]["value"] == complex(3.0)

    manager.set_leaf_parameter_value("a", 5.5)
    params2 = manager.get_all_parameters()
    assert params2["sum_ab"]["value"] == complex(5.5 + 2.0)

    m_mu = manager.get_particle_mass(13)
    assert m_mu == pytest.approx(0.105658 + 0j, rel=1e-9)
