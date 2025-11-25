from SetAnubis.core.MadGraph.domain.CommandSectionType import CommandSectionType
from SetAnubis.core.MadGraph.domain.MadGraphCommandSection import MadGraphCommandSection
from SetAnubis.core.MadGraph.domain.MadGraphCommandConfig import MadGraphCommandConfig

from pathlib import Path

class MadGraphCommandCard:
    """Class to construct and manage MadGraph command card configurations.

    Attributes:
        config: Configuration object containing model paths and settings.
    """
    def __init__(self, config : MadGraphCommandConfig):
        """Initializes MadGraphCommandCard with a configuration.

        Args:
            config: Configuration settings for MadGraph generation.
        """
        self.config : MadGraphCommandConfig = config
        self.head = None
        self.tail = None
        self._build_default_structure()

    def _build_default_structure(self):
        """Constructs the default sections of a MadGraph command card."""
        self.add_section(CommandSectionType.HEADER, self._default_header())
        self.add_section(CommandSectionType.BASE_MODEL, "import model sm")
        self.add_section(CommandSectionType.DEFINITIONS, self._default_definitions())
        self.add_model_import(self.config.neo_set_anubis.get_ufo_path())

    def add_section(self, section_type, content):
        """Adds a section to the command card.

        Args:
            section_type (CommandSectionType): Type of command section.
            content (str): Content for the section.
        """
        section = MadGraphCommandSection(section_type, content)
        if not self.head:
            self.head = self.tail = section
        else:
            self.tail.next = section
            self.tail = section

    def add_model_import(self, ufo_path):
        """Imports a UFO model based on the provided path.

        Args:
            ufo_path (str): Path to the UFO model.
        """
        model_name = Path(ufo_path).name
        if self.config.model_in_madgraph != "":
            self.add_section(CommandSectionType.MODEL_IMPORT, f"import model {self.config.model_in_madgraph}")
        else:
            self.add_section(CommandSectionType.MODEL_IMPORT, f"import model {model_name}")

    def add_process(self, command):
        """Adds a process command to the card.

        Args:
            command (str): MadGraph command to add.

        Raises:
            ValueError: If the provided command is invalid.
        """
        if "generate" in command:
            self.add_section(CommandSectionType.PROCESS, command)
        elif "add process" in command:
            self.add_section(CommandSectionType.PROCESS, command)
        elif "compute_widths" in command:
            self.add_section(CommandSectionType.PROCESS, command)
        else:
            raise ValueError("Invalid process command")

    def set_output_launch(self, name):
        """Sets the output and launch commands.

        Args:
            name (str): Name for the output directory.
        """
        if not self.config.cache:
            self.add_section(CommandSectionType.OUTPUT, f"output {name}")
        self.add_section(CommandSectionType.LAUNCH, f"launch {name}")

    def configure_cards(self):
        """Configures additional cards based on the simulation setup."""
        paths = [
            "/External_Integration/input_files/param_card.dat",
            "/External_Integration/input_files/run_card.dat"
        ]
        if self.config.shower:
            paths.append("/External_Integration/input_files/pythia8_card.dat")
            self.add_section(CommandSectionType.SHOWER, f"shower={self.config.shower}")
        if self.config.madspin:
            paths.append("/External_Integration/input_files/madspin_card.dat")
            self.add_section(CommandSectionType.MADSPIN, f"madspin={self.config.madspin}")
        self.add_section(CommandSectionType.CARDS, "\n".join(paths))

    def add_W_parameter(self, key: str):
        """Adds a parameter starting with 'W' to the card with value 'auto'.
        
        Args:
            key (str): The parameter name, must start with 'W'.
        
        Raises:
            ValueError: If the key does not start with 'W'.
        """
        if not key.startswith('W'):
            raise ValueError("Key must start with 'W'")
        self.add_section(CommandSectionType.PARAMETERS, f"set {key} auto")
        
    def add_parameter_scan(self, key, values):
        val = f"scan:{values}" if isinstance(values, str) else f"scan:{values!r}"
        self.add_section(CommandSectionType.PARAMETERS, f"set {key} {val}")

    def serialize(self):
        """Serializes the command card into a string format.

        Returns:
            str: Serialized MadGraph command card.
        """
        lines = []
        current = self.head
        while current:
            lines.append(str(current))
            current = current.next
        return "\n\n".join(lines)

    @classmethod
    def deserialize(cls, text: str):
        """Provides default header content for the command card.

        Returns:
            str: Default header content.
        """
        sections = text.strip().split("\n\n")
        card = cls(config=None)  # will fix this later
        card.head = card.tail = None
        for sec in sections:
            card.add_section(CommandSectionType.FOOTER, sec)
        return card

    def _default_header(self):
        return """# ************************************************************
#* MadGraph5_aMC@NLO *
#* Autogenerated by MadGraphCommandCard *
# ************************************************************"""

    def _default_definitions(self):
        """Provides default definitions section for the command card.

        Returns:
            str: Definitions content.
        """
        return "\n".join([
            "define p = g u c d s u~ c~ d~ s~",
            "define j = g u c d s u~ c~ d~ s~",
            "define vv = ve ve~",
            "define ell = e+ e-",
            "define q = u c d s u~ c~ d~ s~",
            "set automatic_html_opening False"
        ])
