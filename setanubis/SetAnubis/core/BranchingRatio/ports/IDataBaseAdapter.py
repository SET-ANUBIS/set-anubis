"""Port used by branching-ratio services to access cached data."""

from abc import ABC, abstractmethod
from typing import Any


class IDataBaseAdapter(ABC):
    """Expose cached branching-ratio data independently of its storage backend."""

    @abstractmethod
    def get(self) -> Any:
        """Return the cache payload supplied by the storage adapter."""
        raise NotImplementedError
