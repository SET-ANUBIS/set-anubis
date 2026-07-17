"""Input port for QCD running quantities."""

from abc import ABC, abstractmethod
from typing import Any


class IQCD(ABC):
    """Provide the running strong coupling and quark masses."""

    @abstractmethod
    def alpha_s(self, Q: float) -> float:
        """Return the strong coupling at scale ``Q``."""
        raise NotImplementedError

    @abstractmethod
    def running_mass(
        self,
        mass: float,
        Q_i: float,
        Q_f: float,
        mass_b_type: Any = None,
        mass_t_type: Any = None,
    ) -> float:
        """Evolve a quark mass from ``Q_i`` to ``Q_f``."""
        raise NotImplementedError
