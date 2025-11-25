from SetAnubis.core.MadGraph.ports.IJobScriptBuilder import IJobScriptBuilder
from SetAnubis.core.MadGraph.ports.ICardWriter import ICardWriter
from SetAnubis.core.MadGraph.domain.MadGraphCommandCard import MadGraphCommandCard
from SetAnubis.core.MadGraph.domain.MadGraphCommandConfig import MadGraphCommandConfig

class JobScriptBuilder(IJobScriptBuilder, ICardWriter):
    """
    Implementation of a job script builder and card writer for MadGraph.

    This class wraps around a `MadGraphCommandCard` instance to build MadGraph
    process definitions, configure scans, manage output naming, and generate 
    full configuration scripts.

    Args:
        config (MadGraphCommandConfig): Configuration object used to initialize 
            the command card builder.

    Attributes:
        builder (MadGraphCommandCard): Internal command card manager handling 
            script generation and parameter configuration.
    """
    def __init__(self, config : MadGraphCommandConfig):
        self.builder = MadGraphCommandCard(config)

    def add_process(self, command: str) -> None:
        """
        Add a MadGraph process definition to the job script.

        Args:
            command (str): A string defining the MadGraph process to be added.

        Returns:
            None
        """
        self.builder.add_process(command)

    def add_auto_width(self, key : str):
        """
        Set a width to auto (calculated at run time by madgraph)

        Args:
            key (str): The name of the width to set in auto.

        Returns:
            None
        """
        self.builder.add_W_parameter(key)
        
    def add_special_section(self, section_type, content):
        """
        Add a special line in the jobscript

        Args:
            section_type (str): The Type in the Enum where the command should go.
            content (str): The content of the Command.
        Returns:
            None
        """
        self.builder.add_section(section_type, content)
        
    def add_parameter_scan(self, key: str, values) -> None:
        """
        Add a parameter scan to the script, varying a parameter over a range or list of values.

        Args:
            key (str): The name of the parameter to scan.
            values: A list or iterable of values to assign to the parameter during the scan.

        Returns:
            None
        """
        self.builder.add_parameter_scan(key, values)

    def set_output_launch(self, name: str) -> None:
        """
        Set the name of the output directory for the MadGraph job launch.

        Args:
            name (str): The name or identifier to use for the launch output.

        Returns:
            None
        """
        self.builder.set_output_launch(name)

    def configure_cards(self) -> None:
        """
        Configure the necessary cards (e.g., run, param, and proc cards) for MadGraph.

        Returns:
            None
        """
        self.builder.configure_cards()

    def serialize(self) -> str:
        """
        Serialize the full command script into a single string.

        Returns:
            str: The complete script representing the MadGraph job configuration.
        """
        return self.builder.serialize()
