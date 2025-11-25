from typing import Callable, Dict, Any, Set
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation

class DecayUFOManager:
    """
    Classe "interne" gérant l'UFO et créant des fonctions de decay 
    en fonction des paramètres. 
    (Implémentation simplifiée, à adapter selon ton UFO.)
    """
    def __init__(self, ufo_path: str):
        self.ufo_path = ufo_path
        self.func = {}  # type: Dict[int, Dict[frozenset, Callable[[Dict[str, Any]], float]]]

    def evaluate_with_sm(self):
        pass

    def create_func_caches(self):
        # On peuple self.func[mother][frozenset({daughter1, ...})] = fonction
        pass

    def get_caches(self):
        return self.func

class DecayProvider(IDecayCalculation):
    """
    Implémentation concrète de IDecayCalculation basée sur l'UFO.
    """
    def __init__(self, ufo_path: str):
        self.decay_manager = DecayUFOManager(ufo_path)
        self.decay_manager.evaluate_with_sm()
        self.decay_manager.create_func_caches()
    
    def get_function(self, mother: int, daughters: Set[int]) -> Callable[[Dict[str, Any]], float]:
        try:
            return self.decay_manager.func[mother][frozenset(daughters)]
        except KeyError:
            raise KeyError(f"No UFO decay function for mother={mother}, daughters={daughters}")

    def calculate(self, 
                  mother: int, 
                  daughters: Set[int], 
                  parameters: Dict[str, float]) -> float:
        func = self.get_function(mother, daughters)
        return func(parameters)

    def get_caches(self):
        return self.decay_manager.get_caches()
