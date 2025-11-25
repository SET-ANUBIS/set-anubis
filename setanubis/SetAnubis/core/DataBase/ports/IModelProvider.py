from abc import ABC, abstractmethod
from enum import Enum

class IModelProvider(ABC):

    @abstractmethod
    def get(self, param : Enum):
        pass