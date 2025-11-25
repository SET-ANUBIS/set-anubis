from abc import ABC,abstractmethod
from enum import Enum
from typing import Dict, Any
class IParticleJSONProxy:
    @abstractmethod
    def get_all_particles(self) -> Dict[int, Dict[str, Any]]:
        pass