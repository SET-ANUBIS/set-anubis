from abc import ABC, abstractmethod

class ICalculatorLoader(ABC):
    @staticmethod
    @abstractmethod
    def load_calculator(script_path: str):
        pass