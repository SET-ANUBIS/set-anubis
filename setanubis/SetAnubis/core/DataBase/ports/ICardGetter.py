from abc import ABC, abstractmethod
from enum import Enum

class ICardGetter(ABC):
    """
    Port interface for the Card generation part (madgraph)
    """
    
    @staticmethod
    @abstractmethod
    def get(type : Enum) -> str:
        """
        Get template card for madgraph
        """
        pass

