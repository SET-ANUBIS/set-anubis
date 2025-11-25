from SetAnubis.core.Madgraph.domain.CommandSectionType import CommandSectionType

class MadGraphCommandSection:
    """Class representing a section within a MadGraph command card.

    Attributes:
        section_type (CommandSectionType): Type of the MadGraph command section.
        content (str): Content of the command section.
        next (MadGraphCommandSection, optional): Reference to the next section. Defaults to None.
    """
    
    def __init__(self, section_type: CommandSectionType, content: str):
        """Initializes a MadGraph command section.

        Args:
            section_type (CommandSectionType): Type of section.
            content (str): Section content.
        """
        self.section_type = section_type
        self.content = content.strip()
        self.next = None

    def __str__(self):
        """Returns the content of the command section.

        Returns:
            str: Content of the section.
        """
        return self.content
