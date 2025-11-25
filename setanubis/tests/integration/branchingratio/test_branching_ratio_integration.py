import csv
import textwrap
import pytest

import SetAnubis.core.BranchingRatio.domain.BranchingRatioManager as br_mod
from SetAnubis.core.BranchingRatio.domain.CalculationStrategy import CalculationDecayStrategy
from SetAnubis.core.BranchingRatio.domain.BranchingRatioManager import Unit


class FakeNSA:
    def __init__(self, masses, params):
        self._m = {int(k): complex(v) for k, v in masses.items()}
        self._p = dict(params)
    def get_particle_mass(self, pdg): return self._m[int(abs(pdg))]
    def get_all_parameters(self):     return dict(self._p)

class NoopChecker:
    def check_decay_validity(self, mother, daughters, nsa): pass


@pytest.fixture(autouse=True)
def patch_unused_adapters(monkeypatch):
    class ZeroAdapter:
        def __init__(self, *a, **k): self._is_br = False
        def is_br(self): return False
        def calculate(self, *a, **k): return 0.0
    monkeypatch.setattr(br_mod, "UFOCalculationAdapter", ZeroAdapter, raising=True)
    monkeypatch.setattr(br_mod, "MadGraphCalculationAdapter", ZeroAdapter, raising=True)
    monkeypatch.setattr(br_mod, "MartyCalculationAdapter", ZeroAdapter, raising=True)


def test_python_adapter_via_loader(tmp_path):
    script = tmp_path / "my_calc.py"
    script.write_text(textwrap.dedent("""
        from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
        class MyCalc(IDecayCalculation):
            def __init__(self): super().__init__()
            def calculate(self, mother, daughters, parameters):
                # BR directe: 2*g
                return 2.0 * float(parameters.get("g", 0.0))
    """), encoding="utf-8")

    checker = NoopChecker()
    nsa = FakeNSA(masses={100: 10.0, 1: 1.0, 2: 2.0}, params={"g": 0.3})
    mgr = br_mod.BranchingRatioManager(checker, nsa)

    mgr.add_decay(
        mother=100,
        daughters=[1,2],
        strategy=CalculationDecayStrategy.PYTHON,
        config={"script_path": str(script), "BR": True}
    )
    brs = mgr.calculate_branching_ratios_for_mother(100)
    assert len(brs) == 1 and brs[0]["branching_ratio"] == pytest.approx(0.6, rel=1e-12)


def test_file_interpolation_adapter_with_csv(tmp_path):
    csv_path = tmp_path / "grid.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["g", "100:1;2"])
        writer.writeheader()
        writer.writerow({"g": "0.4", "100:1;2": "1.23"})

    checker = NoopChecker()
    nsa = FakeNSA(masses={100: 5.0, 1: 1.0, 2: 2.0}, params={"g": 0.4})
    mgr = br_mod.BranchingRatioManager(checker, nsa)

    mgr.add_decay(
        mother=100,
        daughters=[1,2],
        strategy=CalculationDecayStrategy.FILE_INTERPOLATION,
        config={"file_path": str(csv_path), "varying_params": ["g"], "BR": False}
    )
    total = mgr.calculate_total_decay(100)
    assert total == pytest.approx(1.23, rel=1e-12)
    brs = mgr.calculate_branching_ratios_for_mother(100)
    assert brs[0]["branching_ratio"] == pytest.approx(1.0, rel=1e-12)
