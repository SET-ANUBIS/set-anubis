from SetAnubis.core.DataBase.domain.UFOTree import ExpressionTree
from SetAnubis.core.DataBase.ports.IUFOParamInterface import IUFOInterface
from SetAnubis.core.DataBase.domain.UFOManager import UFOManager

class UFOInterface(IUFOInterface):
    """Interface for managing and retrieving UFO parameter trees."""
    
    def __init__(self, ufo_path : str):
        """Initializes the UFO interface with the given path.

        Args:
            ufo_path (str): Path to the UFO model directory.
        """
        self.ufo_manager = UFOManager(ufo_path)
    
    def get_tree(self) -> ExpressionTree:
        """Retrieves the parameter expression tree from the UFO manager.

        Returns:
            ExpressionTree: The UFO parameter expression tree.
        """
        return self.ufo_manager.get_param_tree()