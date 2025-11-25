from SetAnubis.core.BranchingRatio.domain.DecayChecker import DecayChecker
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.domain.CalculationStrategy import CalculationDecayStrategy
from SetAnubis.core.BranchingRatio.domain.BranchingRatioManager import BranchingRatioManager, Unit
from SetAnubis.core.Common.MultiSet import MultiSet

class MockCalculationStrategy:
    def __init__(self, width: float, is_br: bool = False):
        self._width = width
        self._is_br = is_br

    def calculate(self, mother, daughters, params: dict) -> float:
        return self._width

    def is_br(self):
        return self._is_br
    
    
def main():
    # Fake mass table
    
    nsa = SetAnubisInterface("Assets/UFO/UFO_HNL")
    
    
    masses = {
        24: 10.0,  # Mother
        2: 2.0,
        -2: 3.0
    }

    checker = DecayChecker()
    manager = BranchingRatioManager(checker, nsa)

    # Add a decay with width = 0.005 (GeV)
    mother = 24
    daughters = MultiSet([-2, 2])
    decay_width = 0.005  # GeV
    mock_strategy = MockCalculationStrategy(width=decay_width)
    manager._decays[(mother, tuple(sorted(daughters)))] = mock_strategy

    print("=== Test 1: Lifetime fallback to 1 / total width ===")
    lifetime_invgev = manager.calculate_lifetime(24, Unit.INVGEV)
    lifetime_s = manager.calculate_lifetime(24, Unit.S)
    print(f"Lifetime of particle 24 (GeV⁻¹): {lifetime_invgev:.3e}")
    print(f"Lifetime of particle 24 (s): {lifetime_s:.3e}")

    print("\n=== Test 2: Manually set lifetime ===")
    manager.add_special_lifetime(24, 1e-10, Unit.S)
    print("Overriding lifetime to 1e-10 s")
    new_lifetime_invgev = manager.calculate_lifetime(24, Unit.INVGEV)
    new_lifetime_mm = manager.calculate_lifetime(24, Unit.MM)
    print(f"Lifetime of particle 24 (GeV⁻¹): {new_lifetime_invgev:.3e}")
    print(f"Lifetime of particle 24 (mm): {new_lifetime_mm:.3e}")

if __name__ == "__main__":
    main()