from enum import Enum

class Specials(Enum):
    TAU0 = "tau0"
    MEMODE = "memode"
    RESONANCE = "resonance"

class GeneralParams(Enum):
    tau0Max = "tau0Max"
    pTHatMin = "pTHatMin"
    
class GeneralType(Enum):
    ParticleDecays = "ParticleDecays"
    PhaseSpace = "PhaseSpace"