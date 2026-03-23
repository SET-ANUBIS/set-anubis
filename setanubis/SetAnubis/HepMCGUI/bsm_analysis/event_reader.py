from __future__ import annotations

from functools import lru_cache
from typing import Optional

from .sources import HepMCFileSource


@lru_cache(maxsize=64)
def load_event_from_hepmc(path: str, event_index: int):
    """Load a single event from a HepMC file by its zero-based index.

    The loaded event is cached in-process to speed up interactive event
    browsing and repeated access to the same file/index pair.

    Args:
        path: Path to the HepMC file to read.
        event_index: Zero-based index of the event to load.

    Returns:
        The HepMC event object located at ``event_index``.

    Raises:
        IndexError: If ``event_index`` does not exist in the file.

    Notes:
        The cache is process-local and keyed by ``(path, event_index)``.
        This function iterates through the file until the requested event
        is found.
    """
    src = HepMCFileSource(path=path)
    for i, ev in enumerate(src):
        if i == int(event_index):
            return ev
    raise IndexError(f"Event index {event_index} not found in file")
