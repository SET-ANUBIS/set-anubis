from SetAnubis.core.DataBase.adapters.FileCopyBuilder import FileCopyBuilder
from pathlib import Path

class MartyFileCopyBuilder:
    def __init__(self):
        self.builder = FileCopyBuilder()

    def add_file(self, src: Path, dest: Path, modifications: list[tuple[str, str]] = None):
        """Ajoute un fichier à copier, avec éventuellement des modifications."""
        return self.builder.add_file(src, dest, modifications)

    def execute(self):
        self.builder.execute()