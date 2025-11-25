import re
from typing import List, Optional


class RunCardLine:
    def __init__(self, raw: str):
        self.raw = raw.rstrip("\n")
        self.key = None
        self.value = None
        self.comment = None

        self._parse()

    def _parse(self):
        if "=" in self.raw and not self.raw.strip().startswith("#"):
            match = re.match(r"^\s*(.*?)\s*=\s*(\w+)\s*(?:! *(.*))?", self.raw)
            if match:
                self.value = match.group(1).strip()
                self.key = match.group(2).strip()
                self.comment = match.group(3).strip() if match.group(3) else None

    def update_value(self, new_value):
        self.value = str(new_value)
        if self.key:
            comment_part = f" ! {self.comment}" if self.comment else ""
            self.raw = f"  {self.value:<10} = {self.key:<20}{comment_part}"

    def __str__(self):
        return self.raw


class RunCardEditor:
    def __init__(self, content: str):
        self.lines: List[RunCardLine] = [
            RunCardLine(line) for line in content.strip().split("\n")
        ]

    @classmethod
    def from_file(cls, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            return cls(f.read())

    def to_file(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.serialize())

    def serialize(self) -> str:
        return "\n".join(str(line) for line in self.lines)

    def get(self, key: str) -> Optional[str]:
        for line in self.lines:
            if line.key == key:
                return line.value
        return None

    def set(self, key: str, value):
        for line in self.lines:
            if line.key == key:
                line.update_value(value)
                return
        self.lines.append(RunCardLine(f"{value} = {key}"))

    def keys(self):
        return [line.key for line in self.lines if line.key]

    def items(self):
        return {line.key: line.value for line in self.lines if line.key}
