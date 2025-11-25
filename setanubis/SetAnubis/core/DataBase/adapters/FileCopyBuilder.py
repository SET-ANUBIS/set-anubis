from pathlib import Path
import shutil
import os

class FileCopyBuilder:
    def __init__(self):
        self.files = []

    def add_file(self, src: Path, dest: Path, modifications: list[tuple[str, str]] = None):
        """Ajoute un fichier à copier, avec éventuellement des modifications."""
        self.files.append({
            "src": src,
            "dest": dest,
            "modifications": modifications or []
        })
        return self

    def execute(self):
        for file_info in self.files:
            src = file_info["src"]
            
            if not os.path.exists(src):
                raise FileNotFoundError(f"Le fichier source n'existe pas : {src}")

            dest = file_info["dest"]
            modifications = file_info["modifications"]

            dest.parent.mkdir(parents=True, exist_ok=True)

            if modifications:
                with src.open("r", encoding="utf-8") as f:
                    content = f.read()
                for pattern, replacement in modifications:
                    content = content.replace(pattern, replacement)
                with dest.open("w", encoding="utf-8") as f:
                    f.write(content)
            elif not os.path.exists(dest) or not os.path.samefile(src, dest):
                shutil.copy2(src, dest)