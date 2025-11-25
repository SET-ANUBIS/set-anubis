from abc import ABC,abstractmethod
from enum import Enum

class IUFOGetter:
    @abstractmethod
    def get(type : Enum):
        pass