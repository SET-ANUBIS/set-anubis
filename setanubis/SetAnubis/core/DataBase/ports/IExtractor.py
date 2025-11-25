from abc import ABC, abstractmethod

class IExtractor(ABC):
    @staticmethod
    @abstractmethod
    def extract(path):
        pass