from SetAnubis.core.MadGraph.ports.ICardInitializer import ICardInitializer
from SetAnubis.core.DataBase.adapters.ParamCardGeneratorAdapter import ParamCardGeneratorAdapter

class ParamCardInitializer(ICardInitializer):
    """
    Port interface for the Card generation part (madgraph)
    """
    def __init__(self, path):
        self.path = path
        
    def generate(self) -> str:
        """
        Generate card for madgraph
        """
        return ParamCardGeneratorAdapter(self.path).generate()

