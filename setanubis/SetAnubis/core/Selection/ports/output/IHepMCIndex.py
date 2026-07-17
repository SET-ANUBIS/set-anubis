"""Output port for writing a searchable HepMC index."""

from typing import List, Protocol

from SetAnubis.core.Selection.domain.Models import (
    HepmcRef,
    IndexWriteResult,
    IndexWriterConfig,
)


class HepmcIndexPort(Protocol):
    """Write or update an index from a collection of HepMC references."""

    def write_index(
        self,
        items: List[HepmcRef],
        cfg: IndexWriterConfig,
    ) -> IndexWriteResult:
        """Persist ``items`` according to ``cfg`` and return the write result."""
        ...
