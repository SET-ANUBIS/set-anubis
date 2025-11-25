from abc import ABC, abstractmethod

class ICardInitializer(ABC):
    """
    Port interface for the Card generation part (madgraph)
    """
    
    @abstractmethod
    def generate(self) -> str:
        """
        Generate card for madgraph
        """
        pass

