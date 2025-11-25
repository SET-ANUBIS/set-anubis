from SetAnubis.core.Madgraph.domain.MadspinSectionType import MadSpinSectionType

class MadSpinSection:
    def __init__(self, section_type: MadSpinSectionType, content: str):
        self.section_type = section_type
        self.content = content.strip()
        self.next = None

    def __str__(self):
        return self.content