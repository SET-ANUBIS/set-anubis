"""MARTY-specific facade over the generic file-copy builder."""

from pathlib import Path
from typing import Optional

from SetAnubis.core.DataBase.adapters.FileCopyBuilder import FileCopyBuilder


class MartyFileCopyBuilder:
    """Queue and execute file copies required by a MARTY workspace."""

    def __init__(self) -> None:
        """Create an empty copy queue."""
        self.builder = FileCopyBuilder()

    def add_file(
        self,
        src: Path,
        dest: Path,
        modifications: Optional[list[tuple[str, str]]] = None,
    ):
        """Queue a file copy with optional text replacements."""
        return self.builder.add_file(src, dest, modifications)

    def execute(self) -> None:
        """Execute every queued copy operation."""
        self.builder.execute()
