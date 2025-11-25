from SetAnubis.core.Madgraph.ports.IMadSpinCardBuilder import IMadSpinCardBuilder
from SetAnubis.core.Madgraph.ports.ICardWriter import ICardWriter
from SetAnubis.core.Madgraph.domain.MadspinCardBuilder import MadSpinCardBuilder
from SetAnubis.core.Madgraph.adapters.output.CardAdapter import CardAdapter, CardType

class MadSpinCardAdapter(IMadSpinCardBuilder, ICardWriter):
    """
    Adapter for building and managing a MadSpin decay card.

    This class wraps the `MadSpinCardBuilder`, providing methods to modify
    decay channels and serialize the final card content. It implements both
    the `IMadSpinCardBuilder` and `ICardWriter` interfaces.

    Args:
        template (str): A string template representing the initial MadSpin card 
            to be deserialized and modified.

    Attributes:
        builder (MadSpinCardBuilder): Internal builder for managing MadSpin decay logic.
    """
    def __init__(self):
        madspin_str = CardAdapter.get(CardType.MADSPIN)
        self.builder = MadSpinCardBuilder.deserialize(madspin_str)

    def add_decay(self, decay_line: str) -> None:
        """
        Add a decay definition to the MadSpin card.

        Args:
            decay_line (str): A string representing a decay process, e.g., "decay t > b w+"

        Returns:
            None
        """
        self.builder.add_decay(decay_line)

    def clear_decays(self) -> None:
        """
        Remove all existing decay definitions from the MadSpin card.

        Returns:
            None
        """
        self.builder.clear_decays()

    def serialize(self) -> str:
        """
        Serialize the current state of the MadSpin card into a string.

        Returns:
            str: The complete content of the MadSpin card.
        """
        return self.builder.serialize()