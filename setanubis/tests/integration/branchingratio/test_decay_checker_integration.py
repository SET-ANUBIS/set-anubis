import pytest

import SetAnubis.core.BranchingRatio.domain.BranchingRatioManager as br_mod
from SetAnubis.core.BranchingRatio.domain.CalculationStrategy import CalculationDecayStrategy
from SetAnubis.core.BranchingRatio.domain.DecayChecker import DecayChecker

class FakeNSA:
    def __init__(self):
        self._m = {
            23: 91.0,     # Z
            11: 0.000511, # e-
            13: 0.105,    # mu-
            22: 0.0,      # photon
        }
        self._charges_pos = {11: -1.0, 13: -1.0, 22: 0.0, 23: 0.0}

    def get_particle_mass(self, pdg):
        return complex(self._m.get(abs(pdg), 0.0))

    def get_particle_info(self, pdg_code):
        if pdg_code >= 0:
            ch = self._charges_pos.get(pdg_code, 0.0)
        else:
            ch = -self._charges_pos.get(abs(pdg_code), 0.0)
        return {"charge": ch}

    def get_all_parameters(self):
        return {"g": 0.0}


class ConstAdapter:
    """Adapter de calcul qui renvoie une largeur partielle constante."""
    def __init__(self, *a, **k): self._is_br = False
    def is_br(self): return False
    def calculate(self, mother, daughters, parameters): return 1.0


@pytest.fixture(autouse=True)
def patch_adapters(monkeypatch):
    monkeypatch.setattr(br_mod, "UFOCalculationAdapter", ConstAdapter, raising=True)
    monkeypatch.setattr(br_mod, "PythonCalculationAdapter", ConstAdapter, raising=True)
    monkeypatch.setattr(br_mod, "FileInterpolationCalculationAdapter", ConstAdapter, raising=True)
    monkeypatch.setattr(br_mod, "MadGraphCalculationAdapter", ConstAdapter, raising=True)
    monkeypatch.setattr(br_mod, "MartyCalculationAdapter", ConstAdapter, raising=True)


def test_add_decay_rejects_invalid_charge():
    mgr = br_mod.BranchingRatioManager(DecayChecker(), FakeNSA())
    with pytest.raises(ValueError, match="Charge not conserved"):
        mgr.add_decay(
            mother=23,
            daughters=[11, 11],
            strategy=CalculationDecayStrategy.PYTHON,
            config={"script_path": "ignored.py", "BR": False},
        )


def test_valid_decays_and_brs():
    mgr = br_mod.BranchingRatioManager(DecayChecker(), FakeNSA())
    #  - Z -> e- + e+
    #  - Z -> mu- + mu+
    mgr.add_decay(23, [11, -11], CalculationDecayStrategy.PYTHON, {"script_path": "x.py", "BR": False})
    mgr.add_decay(23, [13, -13], CalculationDecayStrategy.PYTHON, {"script_path": "y.py", "BR": False})

    brs = mgr.calculate_branching_ratios_for_mother(23)
    # 1.0 -> total=2.0 -> each BR=0.5
    assert len(brs) == 2
    for entry in brs:
        assert entry["partial_width"] == pytest.approx(1.0, rel=1e-12)
        assert entry["branching_ratio"] == pytest.approx(0.5, rel=1e-12)
