from SetAnubis.core.ModelCore.ports.output.IUFOGetter import IUFOGetter
from SetAnubis.core.DataBase.adapters.UFOInterface import UFOInterface, ExpressionTree

class UFOGetter(IUFOGetter):
    """Class to retrieve UFO parameter trees using a UFO interface.

    Attributes:
        ufo_interface (UFOInterface): Interface instance to interact with UFO models.
    """
    def __init__(self, ufo_path):
        """Initializes UFOGetter with a path to the UFO model.

        Args:
            ufo_path (str): Path to the UFO model.
        """
        self.ufo_interface = UFOInterface(ufo_path)
    
    def get(self) -> ExpressionTree:
        """Retrieves the parameter tree from the UFO interface.

        Returns:
            ExpressionTree: The UFO parameter expression tree.
        """
        return self.ufo_interface.get_tree()