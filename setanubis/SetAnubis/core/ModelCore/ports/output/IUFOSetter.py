from abc import ABC, abstractmethod

class IUFOsetter(ABC):
    @abstractmethod
    def set(type, elem, value):
        pass