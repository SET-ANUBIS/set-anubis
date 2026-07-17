"""Provide a small pure-Python decay calculator used by branching-ratio examples."""

from typing import Dict, Any, Set
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation

class MyPythonDecayCalc(IDecayCalculation):
    """Return a deliberately simple, non-physical partial-width estimate."""

    def calculate(self, 
                  mother: int, 
                  daughters: Set[int], 
                  parameters: Dict[str, float]) -> float:
        alpha_em = parameters.get("alpha_em", 1/137.0)

        # This toy formula exists only to demonstrate the provider contract.
        partial_width = alpha_em * float(mother) / 1e3

        return partial_width
