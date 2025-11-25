from SetAnubis.core.DataBase.ports.ICardGenerator import ICardGenerator
from SetAnubis.core.DataBase.domain.ParamCardGenerator import ParamCardGenerator

class ParamCardGeneratorAdapter(ICardGenerator):
    """Adapter class to generate parameter cards using a generic template."""
    
    def __init__(self, path : str):
        """Initializes the adapter with a path to parameter definitions.

        Args:
            path (str): Path to parameter definitions.
        """
        self.path = path
    def generate(self) -> str:
        """Generates a parameter card from the provided path.

        Returns:
            str: Generated parameter card content.
        """
        return ParamCardGenerator(self.path).generate_param_card(generic=True)

