from typing import Callable, Dict, Any, Set
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation

class DecayUFOManager:
    """Manage UFO-backed decay functions for branching-ratio calculations.

    This lightweight implementation provides the cache contract expected by
    :class:`DecayProvider`; concrete UFO evaluation can populate ``func``.
    """
    def __init__(self, ufo_path: str):
        self.ufo_path = ufo_path
        self.func = {}  # type: Dict[int, Dict[frozenset, Callable[[Dict[str, Any]], float]]]

    def evaluate_with_sm(self):
        pass

    def create_func_caches(self):
        # Populate self.func[mother][frozenset({daughter1, ...})] with callables.
        pass

    def get_caches(self):
        return self.func

class DecayProvider(IDecayCalculation):
    """Concrete :class:`IDecayCalculation` backed by a UFO decay manager."""
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
