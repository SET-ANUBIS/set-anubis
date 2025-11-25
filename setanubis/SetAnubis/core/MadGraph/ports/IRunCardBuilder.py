from abc import ABC, abstractmethod
from typing import Optional

class IRunCardBuilder(ABC):
    """
    Port interface for reading/writing/modifying a MadGraph run_card.dat file.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get the value of a run card parameter."""
        pass

    @abstractmethod
    def set(self, key: str, value) -> None:
        """Set the value of a run card parameter."""
        pass
