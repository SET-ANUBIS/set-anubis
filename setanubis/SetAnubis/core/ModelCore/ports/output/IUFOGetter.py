"""Output port for retrieving parsed UFO model data."""

from abc import ABC, abstractmethod
from typing import Any


class IUFOGetter(ABC):
    """Retrieve the domain representation of a UFO model."""

    @abstractmethod
    def get(self) -> Any:
        """Return the parsed UFO parameter representation."""
        raise NotImplementedError
