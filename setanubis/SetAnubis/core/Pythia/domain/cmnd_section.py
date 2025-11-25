from SetAnubis.core.Pythia.domain.cmnd_section_type import CMNDSectionType

class CMNDSection:
    def __init__(self, section_type: CMNDSectionType, content: str):
        self.section_type = section_type
        self.content = content.strip()
        self.next = None

    def __str__(self):
        return self.content