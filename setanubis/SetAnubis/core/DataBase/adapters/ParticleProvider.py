"""Particle providers backed by a UFO model."""

from __future__ import annotations

from enum import Enum
from typing import Any

from SetAnubis.core.DataBase.domain.UFOManager import UFOManager
from SetAnubis.core.DataBase.ports.IModelProvider import IModelProvider


class ParticleType(Enum):
    """Select the Standard Model, new-physics, or complete particle set."""

    SM = 0
    NEW = 1
    ALL = 2


class ParticleProvider(IModelProvider):
    """Expose particle collections loaded from a UFO model."""

    def __init__(self, ufo_path: str) -> None:
        """Load the UFO model located at ``ufo_path``."""

        self.ufo_manager = UFOManager(ufo_path)

    def get(self, param: ParticleType) -> Any:
        """Return the particle collection selected by ``param``."""

        match param:
            case ParticleType.SM:
                return self.ufo_manager.get_sm_particles(True)
            case ParticleType.NEW:
                return self.ufo_manager.get_new_particles(True)
            case ParticleType.ALL:
                return self.ufo_manager.get_all_particles(True)
        return None
