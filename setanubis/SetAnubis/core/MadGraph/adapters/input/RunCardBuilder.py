from typing import Optional
import numpy as np

from SetAnubis.core.MadGraph.ports.IRunCardBuilder import IRunCardBuilder
from SetAnubis.core.MadGraph.ports.ICardWriter import ICardWriter
from SetAnubis.core.MadGraph.domain.MadGraphRunCardEditor import RunCardEditor as DomainRunCardEditor
from SetAnubis.core.MadGraph.adapters.output.CardAdapter import CardAdapter, CardType


class RunCardBuilder(IRunCardBuilder, ICardWriter):
    """
    Builder and editor for a MadGraph run card.

    This class provides methods to get, set, and serialize configuration values
    for a MadGraph run card. It wraps a `RunCardEditor` instance and implements
    both the `IRunCardBuilder` and `ICardWriter` interfaces.

    Attributes:
        editor (DomainRunCardEditor): Internal editor used to manipulate run card
            values.
        rng (np.random.Generator): Random number generator used to create seeds.
    """

    def __init__(self, rng: Optional[np.random.Generator] = None):
        """
        Initialize the run card builder with a default template.

        Args:
            rng (Optional[np.random.Generator]): Random number generator used for
                seed generation. If None, a default NumPy generator is created.

        Returns:
            None
        """
        runcard_template = CardAdapter.get(CardType.RUNCARD)
        self.editor = DomainRunCardEditor(runcard_template)
        self.rng = rng or np.random.default_rng()

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

    def set_random_seed(self, seed: Optional[int] = None) -> int:
        """
        Set the `iseed` parameter in the run card.

        If no seed is provided, a random seed is generated automatically using
        NumPy.

        Args:
            seed (Optional[int]): The seed value to assign. If None, a random
                seed is generated.

        Returns:
            int: The seed value that was written to the run card.
        """
        if seed is None:
            seed = int(self.rng.integers(1, 2_147_483_647))

        self.set("iseed", seed)
        return seed

    def serialize(self) -> str:
        """
        Serialize the current run card configuration into a string.

        Returns:
            str: The complete content of the run card.
        """
        return self.editor.serialize()