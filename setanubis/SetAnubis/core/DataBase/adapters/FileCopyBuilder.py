"""File-copy adapter with optional in-place text substitutions."""

from __future__ import annotations

import shutil
from pathlib import Path


class FileCopyBuilder:
    """Collect and execute deterministic file-copy operations."""

    def __init__(self) -> None:
        """Create an empty copy plan."""

        self.files: list[dict[str, object]] = []

    def add_file(
        self,
        src: Path,
        dest: Path,
        modifications: list[tuple[str, str]] | None = None,
    ) -> "FileCopyBuilder":
        """Queue a file copy with optional literal text replacements."""

        self.files.append(
            {
                "src": Path(src),
                "dest": Path(dest),
                "modifications": modifications or [],
            }
        )
        return self

    def execute(self) -> None:
        """Execute all queued copy operations in insertion order."""

        for file_info in self.files:
            src = Path(file_info["src"])
            dest = Path(file_info["dest"])
            modifications = list(file_info["modifications"])

            if not src.exists():
                raise FileNotFoundError(f"The source file does not exist: {src}")

            dest.parent.mkdir(parents=True, exist_ok=True)

            if modifications:
                content = src.read_text(encoding="utf-8")
                for pattern, replacement in modifications:
                    content = content.replace(pattern, replacement)
                dest.write_text(content, encoding="utf-8")
            elif not dest.exists() or not src.samefile(dest):
                shutil.copy2(src, dest)
