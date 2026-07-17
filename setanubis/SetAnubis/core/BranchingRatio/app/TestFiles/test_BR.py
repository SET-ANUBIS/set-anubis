# ===========================
# File: my_python_calc.py
# ===========================
from typing import Dict, Any, Set
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation

class MyPythonDecayCalc(IDecayCalculation):
    """
    Minimal demonstration calculation.
    The toy partial width depends on the ``alpha_em`` parameter and the mother
    particle mass. The formula is intentionally illustrative rather than physical.
    """

    def calculate(self, 
                  mother: int, 
                  daughters: Set[int], 
                  parameters: Dict[str, float]) -> float:
        alpha_em = parameters.get("alpha_em", 1/137.0)

        partial_width = alpha_em * float(mother) / 1e3

        return partial_width
