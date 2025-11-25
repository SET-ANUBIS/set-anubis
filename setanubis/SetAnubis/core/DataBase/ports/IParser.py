from abc import ABC, abstractmethod

class IParser(ABC):

    @staticmethod
    @abstractmethod
    def parse(filename):
        pass