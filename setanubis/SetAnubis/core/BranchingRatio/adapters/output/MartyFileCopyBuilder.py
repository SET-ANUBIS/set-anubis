from SetAnubis.core.DataBase.adapters.FileCopyBuilder import FileCopyBuilder
from pathlib import Path

class MartyFileCopyBuilder:
    def __init__(self):
        self.builder = FileCopyBuilder()

    def add_file(self, src: Path, dest: Path, modifications: list[tuple[str, str]] = None):
        """Queue a file copy with optional text replacements."""
        return self.builder.add_file(src, dest, modifications)

    def execute(self):
        self.builder.execute()