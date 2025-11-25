from abc import ABC, abstractmethod
from SetAnubis.core.DataBase.domain.UFOTree import ExpressionTree

class IUFOInterface(ABC):

    @abstractmethod
    def get_tree(self) -> ExpressionTree:
        pass