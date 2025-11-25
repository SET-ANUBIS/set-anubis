from SetAnubis.core.DataBase.ports.IModelProvider import IModelProvider
from SetAnubis.core.DataBase.domain.UFOManager import UFOManager

from enum import Enum

class ParticleType(Enum):
    SM = 0
    NEW = 1
    ALL = 2
        
class ParticleProvider(IModelProvider):

    def __init__(self, ufo_path: str):
        self.ufo_manager = UFOManager(ufo_path)

    def get(self, param: ParticleType):
        match param:
            case ParticleType.SM:
                return self.ufo_manager.get_sm_particles(True)
            case ParticleType.NEW:
                return self.ufo_manager.get_new_particles(True)
            case ParticleType.ALL:
                return self.ufo_manager.get_all_particles(True)
        