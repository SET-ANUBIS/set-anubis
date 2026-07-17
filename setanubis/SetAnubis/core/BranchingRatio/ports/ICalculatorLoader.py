"""Port for loading user-provided decay calculators."""

from abc import ABC, abstractmethod
from typing import Any


class ICalculatorLoader(ABC):
    """Load a decay calculator implementation from a Python source file."""

    @staticmethod
    @abstractmethod
    def load_calculator(script_path: str) -> Any:
        """Load and return the calculator declared by ``script_path``."""
        raise NotImplementedError
