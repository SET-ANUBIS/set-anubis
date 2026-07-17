"""Output port for updating a UFO-backed model representation."""

from abc import ABC, abstractmethod
from typing import Any


class IUFOsetter(ABC):
    """Update one element in a UFO-backed model store."""

    @abstractmethod
    def set(self, type: Any, elem: Any, value: Any) -> None:
        """Store ``value`` for ``elem`` in the selected UFO element type."""
        raise NotImplementedError
