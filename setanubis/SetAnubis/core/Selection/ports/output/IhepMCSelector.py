from typing import Protocol, List
from SetAnubis.core.Selection.domain.Models import HepmcSelectionQuery, HepmcRef

class HepmcSelectorPort(Protocol):
    """Port: sélection d’HEPMC à partir d’une base d’événements."""
    def select(self, query: HepmcSelectionQuery) -> List[HepmcRef]:
        ...
