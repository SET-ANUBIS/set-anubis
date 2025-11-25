from typing import Dict, Any, Set
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation

class MadGraphCalculationAdapter(IDecayCalculation):
    def calculate(self, mother: int, daughters: Set[int], parameters: Dict[str, float]) -> float:
        return 0.0
