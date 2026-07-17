"""Output port for querying HepMC records."""

from typing import List, Protocol

from SetAnubis.core.Selection.domain.Models import HepmcRef, HepmcSelectionQuery


class HepmcSelectorPort(Protocol):
    """Select HepMC references from an event catalogue."""

    def select(self, query: HepmcSelectionQuery) -> List[HepmcRef]:
        """Return references that satisfy ``query``."""
        ...
