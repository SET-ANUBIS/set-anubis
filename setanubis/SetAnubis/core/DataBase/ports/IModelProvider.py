"""Port for retrieving model data from a persistence adapter."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class IModelProvider(ABC):
    """Provide a model value selected by a domain enumeration."""

    @abstractmethod
    def get(self, param: Enum) -> Any:
        """Return the model value associated with ``param``."""
        raise NotImplementedError
