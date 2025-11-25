from typing import Protocol, List
from SetAnubis.core.Selection.domain.Models import HepmcRef, IndexWriterConfig, IndexWriteResult

class HepmcIndexPort(Protocol):
    """Port: écrit/maintient l’index CSV à partir d’une liste d’HEPMC."""
    def write_index(self, items: List[HepmcRef], cfg: IndexWriterConfig) -> IndexWriteResult:
        ...
