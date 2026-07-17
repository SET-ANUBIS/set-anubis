"""Port for parsers that transform source files into domain objects."""

from abc import ABC, abstractmethod
from os import PathLike
from typing import Any


class IParser(ABC):
    """Parse one supported file format into a domain representation."""

    @staticmethod
    @abstractmethod
    def parse(filename: str | PathLike[str]) -> Any:
        """Parse ``filename`` and return the resulting object."""
        raise NotImplementedError
