from enum import Enum

class CMNDSectionType(Enum):
    HEADER = "header"
    GENERAL = "general"
    NEW_PARTICLES = "new_particles"
    NEW_PARTICLES_DECAYS = "new_particles_decays"
    HARD_PRODUCTION = "hard_production"
    SM_PARTICLES_CHANGES = "sm_particles_changes"
    SM_PARTICLES_DECAY_TO_NEW = "sm_particles_decay_to_new"
    SM_PARTICLES_DECAY_TO_SM = "sm_particles_decay_to_sm"
    FOOTER = "footer"