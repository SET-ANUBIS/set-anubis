from abc import ABC, abstractmethod
from typing import Set, Callable, Dict, Tuple, Any

class IDecayProvider(ABC):
    """
    Port interface for Decay UFO Manager.
    Defines required methods to interact with decay functions.
    """
    
    @abstractmethod
    def get_function(self, mother: int, daughters: Set[int]) -> Callable[[Dict[str, Any]], float]:
        """
        Retrieves the decay function for a given mother particle and its daughter particles.
        
        Args:
            mother (int): PDG code of the mother particle.
            daughters (Set[int]): PDG codes of the daughter particles.
        
        Returns:
            Callable[[Dict[str, Any]], float]: A function that computes the decay rate given parameter values.
        """
        pass

    @abstractmethod
    def get_caches(self) -> Tuple[dict, dict]:
        """
        Retrieves the decay cache (param + function).
        
        
        Returns:
            To dict with function (first) and params (second)
        """
        pass