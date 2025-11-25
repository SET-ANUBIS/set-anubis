from typing import Optional
from SetAnubis.core.Madgraph.ports.IRunCardBuilder import IRunCardBuilder
from SetAnubis.core.Madgraph.ports.ICardWriter import ICardWriter
from SetAnubis.core.Madgraph.domain.MadGraphRunCardEditor import RunCardEditor as DomainRunCardEditor
from SetAnubis.core.Madgraph.adapters.output.CardAdapter import CardAdapter, CardType

class PythiaCardBuilder(ICardWriter):
    """
    Builder and editor for a MadGraph pythia card.

    This class for now only use the template and send it back, maybe later will be able to changes

    Args:
        template (str): The initial run card content to be loaded and edited.

    Attributes:
        editor (RunCardEditor): Internal editor used to manipulate run card values.
    """
    def __init__(self):
        py8_template = CardAdapter.get(CardType.PYTHIA8)
        self.py8_template = py8_template


    def serialize(self) -> str:
        """
        Serialize the current run card configuration into a string.

        Returns:
            str: The complete content of the pythia card.
        """
        return self.py8_template