from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol, Optional, Iterator

class EventSource(Protocol):
    """Protocol for iterable event sources.

    An event source is any object that yields ``pyhepmc.GenEvent`` instances
    when iterated over.
    """
    def __iter__(self) -> Iterable["hp.GenEvent"]:
        """Iterate over HepMC events.

        Returns:
            An iterable of ``pyhepmc.GenEvent`` objects.
        """
        ...

@dataclass(frozen=True)
class HepMCFileSource:
    """Event source backed by a HepMC file.

    This source opens the file lazily during iteration and yields events
    one by one.

    Attributes:
        path: Path to the HepMC file.
    """
    path: str

    def __iter__(self) -> Iterator["hp.GenEvent"]:
        """Iterate over events stored in the HepMC file.

        Yields:
            ``pyhepmc.GenEvent`` objects read from ``self.path``.
        """
        import pyhepmc as hp  # local import
        with hp.open(self.path) as f:
            for event in f:
                yield event

def hepmc_unit_name(obj: object, attr: str) -> Optional[str]:
    """Safely read the name of a HepMC unit enum attribute.

    This helper is intended for attributes such as ``momentum_unit`` or
    ``length_unit``. It returns ``None`` when the attribute is missing,
    inaccessible, or does not expose a ``name`` field.

    Args:
        obj: Object holding the unit attribute.
        attr: Name of the attribute to inspect.

    Returns:
        The enum name as a string, or ``None`` if unavailable.
    """
    try:
        u = getattr(obj, attr)
    except Exception:
        return None
    try:
        return getattr(u, "name", None)
    except Exception:
        return None
