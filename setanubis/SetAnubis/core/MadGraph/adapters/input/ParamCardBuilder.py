from SetAnubis.core.MadGraph.ports.ICardWriter import ICardWriter
from SetAnubis.core.MadGraph.adapters.output.ParamCardInitializer import ParamCardInitializer

class ParamCardBuilder(ICardWriter):
    """
    Port interface for the Card generation part (madgraph)
    """
    def __init__(self, path):
        self.param_card = ParamCardInitializer(path).generate()
        
    def serialize(self) -> str:
        """
        Generate card for madgraph
        """
        return self.param_card

