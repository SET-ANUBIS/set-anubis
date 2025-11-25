from abc import ABC, abstractmethod

class IJobScriptBuilder(ABC):
    """
    Port interface for building a MadGraph jobscript (mg5_aMC input file).
    """

    @abstractmethod
    def add_process(self, command: str) -> None: pass

    @abstractmethod
    def add_parameter_scan(self, key: str, values) -> None: pass

    @abstractmethod
    def set_output_launch(self, name: str) -> None: pass

    @abstractmethod
    def configure_cards(self) -> None: pass
