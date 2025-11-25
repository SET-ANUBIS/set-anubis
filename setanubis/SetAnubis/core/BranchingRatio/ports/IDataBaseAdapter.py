from abc import ABC, abstractmethod

class IDataBaseAdapter(ABC):
    @abstractmethod
    def get():
        pass