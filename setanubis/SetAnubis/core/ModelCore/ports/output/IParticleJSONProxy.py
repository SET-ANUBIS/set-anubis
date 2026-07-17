"""Output port for particle metadata loaded from JSON."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IParticleJSONProxy(ABC):
    """Return a normalised particle catalogue from an external JSON source."""

    @abstractmethod
    def get_all_particles(self) -> Dict[int, Dict[str, Any]]:
        """Return particle records keyed by PDG identifier."""
        raise NotImplementedError
