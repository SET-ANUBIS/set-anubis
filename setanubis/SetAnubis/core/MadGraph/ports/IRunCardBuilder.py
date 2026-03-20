from abc import ABC, abstractmethod
from typing import Optional

class IRunCardBuilder(ABC):
    """
    Port interface for reading/writing/modifying a MadGraph run_card.dat file.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """
        Retrieve the value of a parameter from the run card.

        Args:
            key (str): The name of the parameter to retrieve.

        Returns:
            Optional[str]: The current value of the parameter, or None if not found.
        """
        pass

    @abstractmethod
    def set(self, key: str, value) -> None:
        """
        Set or update the value of a parameter in the run card.

        Args:
            key (str): The name of the parameter to set.
            value: The value to assign to the parameter.

        Returns:
            None
        """
        pass
    
    @abstractmethod
    def set_random_seed(self, seed: Optional[int] = None) -> int:
        """
        Set the `iseed` parameter in the run card.

        If no seed is provided, a random seed is generated automatically.

        Args:
            seed (Optional[int]): The seed value to assign. If None, a random
                seed is generated.

        Returns:
            int: The seed value that was written to the run card.
        """
        pass
