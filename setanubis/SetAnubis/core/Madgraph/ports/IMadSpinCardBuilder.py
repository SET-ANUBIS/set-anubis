from abc import ABC, abstractmethod

class IMadSpinCardBuilder(ABC):
    """
    Port interface for managing and customizing a MadSpin card.
    """

    @abstractmethod
    def add_decay(self, decay_line: str) -> None:
        """Add a decay process to the card."""
        pass

    @abstractmethod
    def clear_decays(self) -> None:
        """Remove all decay lines."""
        pass

