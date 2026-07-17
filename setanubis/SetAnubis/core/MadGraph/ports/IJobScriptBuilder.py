"""Input port for constructing a MadGraph command script."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any


class IJobScriptBuilder(ABC):
    """Build an ``mg5_aMC`` command file without performing I/O."""

    @abstractmethod
    def add_process(self, command: str) -> None:
        """Append a MadGraph process-generation command."""
        raise NotImplementedError

    @abstractmethod
    def add_parameter_scan(self, key: str, values: Iterable[Any] | str) -> None:
        """Add scan values for one model parameter."""
        raise NotImplementedError

    @abstractmethod
    def set_output_launch(self, name: str) -> None:
        """Set the MadGraph output and launch directory name."""
        raise NotImplementedError

    @abstractmethod
    def configure_cards(self) -> None:
        """Insert the configured card references into the command script."""
        raise NotImplementedError
