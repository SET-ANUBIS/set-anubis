from typing import Dict, Any, Set
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.BranchingRatio.adapters.output.BRCalculatorLoader import BRCalculatorLoader
from SetAnubis.core.Common.MultiSet import MultiSet

class PythonCalculationAdapter(IDecayCalculation):
    """
    Strategy concrète pour la calculation "PYTHON" (script utilisateur).
    Elle peut charger dynamiquement un script par exemple.
    """

    def __init__(self, script_path: str, is_br = False):
        self._calculator = BRCalculatorLoader.load_calculator(script_path)
        self._is_br = is_br

    def calculate(self, 
                  mother: int, 
                  daughters: MultiSet[int], 
                  parameters: Dict[str, float]) -> float:
        return self._calculator.calculate(mother, daughters, parameters)
