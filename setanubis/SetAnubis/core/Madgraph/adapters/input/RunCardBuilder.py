from typing import Optional
from SetAnubis.core.Madgraph.ports.IRunCardBuilder import IRunCardBuilder
from SetAnubis.core.Madgraph.ports.ICardWriter import ICardWriter
from SetAnubis.core.Madgraph.domain.MadGraphRunCardEditor import RunCardEditor as DomainRunCardEditor
from SetAnubis.core.Madgraph.adapters.output.CardAdapter import CardAdapter, CardType

class RunCardBuilder(IRunCardBuilder, ICardWriter):
    """
    Builder and editor for a MadGraph run card.

    This class provides methods to get, set, and serialize configuration values
    for a MadGraph run card. It wraps a `RunCardEditor` instance and implements
    both the `IRunCardBuilder` and `ICardWriter` interfaces.

    Args:
        template (str): The initial run card content to be loaded and edited.

    Attributes:
        editor (RunCardEditor): Internal editor used to manipulate run card values.
    """
    def __init__(self):
        runcard_template = CardAdapter.get(CardType.RUNCARD)
        self.editor = DomainRunCardEditor(runcard_template)

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve the value of a parameter from the run card.

        Args:
            key (str): The name of the parameter to retrieve.

        Returns:
            Optional[str]: The current value of the parameter, or None if not found.
        """
        return self.editor.get(key)

    def set(self, key: str, value) -> None:
        """
        Set or update the value of a parameter in the run card.

        Args:
            key (str): The name of the parameter to set.
            value: The value to assign to the parameter.

        Returns:
            None
        """
        self.editor.set(key, value)

    def serialize(self) -> str:
        """
        Serialize the current run card configuration into a string.

        Returns:
            str: The complete content of the run card.
        """
        return self.editor.serialize()