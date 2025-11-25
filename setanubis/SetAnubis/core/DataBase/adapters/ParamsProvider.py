from SetAnubis.core.DataBase.ports.IModelProvider import IModelProvider
from SetAnubis.core.DataBase.domain.UFOManager import UFOManager
from SetAnubis.core.DataBase.adapters.ParticleProvider import ParticleType
from enum import Enum

class ParamsProvider(IModelProvider):

    def __init__(self, ufo_path: str):
        self.ufo_manager = UFOManager(ufo_path)

    def get(self, param: ParticleType):
        match param:
            case ParticleType.SM:
                return self.ufo_manager.get_sm_params()
            case ParticleType.NEW:
                return self.ufo_manager.get_param_with_sm_evaluation()
            case ParticleType.ALL:
                return self.ufo_manager.get_param_with_sm_evaluation()
        