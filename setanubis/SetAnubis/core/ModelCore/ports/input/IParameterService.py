"""Input port for model parameters and particle metadata."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IParameterService(ABC):
    """Expose model parameters and particles to the other pipeline domains."""

    @abstractmethod
    def set_leaf_param(self, name: str, value: float) -> None:
        """Set a mutable leaf parameter and refresh dependent values."""
        raise NotImplementedError

    @abstractmethod
    def get_parameter_value(self, name: str) -> float:
        """Return the evaluated numerical value of a model parameter."""
        raise NotImplementedError

    @abstractmethod
    def get_all_parameters(self) -> Dict[str, Any]:
        """Return all known model parameters and their metadata."""
        raise NotImplementedError

    @abstractmethod
    def get_all_particles(self) -> Dict[int, Any]:
        """Return all known particles keyed by PDG identifier."""
        raise NotImplementedError

    @abstractmethod
    def get_particle_info(self, pdg_code: int) -> Dict[str, Any]:
        """Return the metadata for one particle."""
        raise NotImplementedError
