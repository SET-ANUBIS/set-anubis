"""Linked-list section type used by MadSpin card builders."""

from __future__ import annotations

from SetAnubis.core.MadGraph.domain.MadspinSectionType import MadSpinSectionType


class MadSpinSection:
    """Store one normalized MadSpin card section and its successor."""

    def __init__(self, section_type: MadSpinSectionType, content: str) -> None:
        """Create a section with stripped text content."""

        self.section_type = section_type
        self.content = content.strip()
        self.next: MadSpinSection | None = None

    def __str__(self) -> str:
        """Return the serialized section content."""

        return self.content
