from abc import ABC, abstractmethod
from typing import Dict, Any

class IParameterService(ABC):
    @abstractmethod
    def set_leaf_param(self, name: str, value: float):
        pass

    @abstractmethod
    def get_parameter_value(self, name: str) -> float:
        pass

    @abstractmethod
    def get_all_parameters(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_all_particles(self) -> Dict[int, Any]:
        pass

    @abstractmethod
    def get_particle_info(self, pdg_code: int) -> Dict[str, Any]:
        pass
