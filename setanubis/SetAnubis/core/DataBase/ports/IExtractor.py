"""Port for extracting structured data from a file."""

from abc import ABC, abstractmethod
from os import PathLike
from typing import Any


class IExtractor(ABC):
    """Convert an external data file into an in-memory representation."""

    @staticmethod
    @abstractmethod
    def extract(path: str | PathLike[str]) -> Any:
        """Read ``path`` and return its decoded contents."""
        raise NotImplementedError
