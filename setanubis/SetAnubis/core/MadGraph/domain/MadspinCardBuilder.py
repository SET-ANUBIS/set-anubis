from SetAnubis.core.MadGraph.domain.MadspinSectionType import MadSpinSectionType
from SetAnubis.core.MadGraph.domain.MadspinSection import MadSpinSection

class MadSpinCardBuilder:
    def __init__(self):
        self.head = None
        self.tail = None

    def add_section(self, section_type: MadSpinSectionType, content: str):
        section = MadSpinSection(section_type, content)
        if not self.head:
            self.head = self.tail = section
        else:
            self.tail.next = section
            self.tail = section

    def add_decay(self, decay_line: str):
        """Ajoute une ligne decay avant le launch"""
        new_section = MadSpinSection(MadSpinSectionType.DECAY, decay_line)

        current = self.head
        previous = None
        while current:
            if current.section_type == MadSpinSectionType.LAUNCH:
                break
            previous = current
            current = current.next

        if previous:
            new_section.next = previous.next
            previous.next = new_section
        else:
            new_section.next = self.head
            self.head = new_section

    def clear_decays(self):
        """Supprime toutes les lignes de decay"""
        dummy = MadSpinSection(MadSpinSectionType.HEADER, "")
        dummy.next = self.head
        current = dummy
        while current.next:
            if current.next.section_type == MadSpinSectionType.DECAY:
                current.next = current.next.next
            else:
                current = current.next
        self.head = dummy.next

    def serialize(self) -> str:
        lines = []
        current = self.head
        while current:
            lines.append(str(current))
            current = current.next
        return "\n".join(lines)

    @classmethod
    def deserialize(cls, text: str):
        """Construit un builder à partir d’un texte existant"""
        builder = cls()
        lines = text.strip().split("\n")
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue
            if line_strip.startswith("#"):
                builder.add_section(MadSpinSectionType.HEADER, line)
            elif line_strip.startswith("set "):
                builder.add_section(MadSpinSectionType.SET, line)
            elif line_strip.startswith("decay "):
                builder.add_section(MadSpinSectionType.DECAY, line)
            elif line_strip.startswith("launch"):
                builder.add_section(MadSpinSectionType.LAUNCH, line)
            else:
                builder.add_section(MadSpinSectionType.HEADER, line)
        return builder