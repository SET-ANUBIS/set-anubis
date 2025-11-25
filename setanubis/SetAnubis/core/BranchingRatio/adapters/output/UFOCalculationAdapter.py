from typing import Dict, Any, Set
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.BranchingRatio.adapters.output.DecayProvider import DecayProvider

class UFOCalculationAdapter(IDecayCalculation):
    """
    Strategy concrète pour la calculation UFO.
    On peut la construire en lui passant un 'ufo_path' ou autre config.
    """
    def __init__(self, ufo_path: str):
        self._provider = DecayProvider(ufo_path)

    def calculate(self, 
                  mother: int, 
                  daughters: Set[int], 
                  parameters: Dict[str, float]) -> float:
        return self._provider.calculate(mother, daughters, parameters)
