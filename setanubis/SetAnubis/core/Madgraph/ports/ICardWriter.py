from abc import ABC, abstractmethod

class ICardWriter(ABC):
    """
    Port interface for reading/writing a MadGraph file.
    """

    @abstractmethod
    def serialize(self) -> str:
        """Return the full run card as string."""
        pass