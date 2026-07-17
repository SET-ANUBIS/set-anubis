"""Parameter providers backed by a UFO model."""

from __future__ import annotations

from typing import Any

from SetAnubis.core.DataBase.adapters.ParticleProvider import ParticleType
from SetAnubis.core.DataBase.domain.UFOManager import UFOManager
from SetAnubis.core.DataBase.ports.IModelProvider import IModelProvider


class ParamsProvider(IModelProvider):
    """Expose parameter collections loaded from a UFO model."""

    def __init__(self, ufo_path: str) -> None:
        """Load the UFO model located at ``ufo_path``."""

        self.ufo_manager = UFOManager(ufo_path)

    def get(self, param: ParticleType) -> Any:
        """Return Standard Model or fully evaluated model parameters."""

        match param:
            case ParticleType.SM:
                return self.ufo_manager.get_sm_params()
            case ParticleType.NEW | ParticleType.ALL:
                return self.ufo_manager.get_param_with_sm_evaluation()
        return None
