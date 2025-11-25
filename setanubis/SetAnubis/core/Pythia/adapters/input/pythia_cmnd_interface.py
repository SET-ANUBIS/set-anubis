from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface
from SetAnubis.core.Pythia.domain.cmnd_base_generation import CMNDGenerationManager
from SetAnubis.core.Pythia.infrastructure.enums import AbstractEnumProduction
from SetAnubis.core.Pythia.domain.special_cases import Specials, GeneralParams, GeneralType

from pathlib import Path
from typing import List, Dict, Any


class PythiaCMNDInterface:
    """
    Interface for configuring and generating CMND files for Pythia simulations.

    This class provides a high-level API to manage particle definitions, decay setups,
    and hard production processes by delegating tasks to the `CMNDGenerationManager`.

    Args:
        master (NeoSetAnubisInterface): Interface to access model parameters and particles.
        dm (DecayInterface): Interface to manage particle decays.

    Attributes:
        manager (CMNDGenerationManager): Internal manager handling CMND generation logic.
    """
    def __init__(self, master : SetAnubisInterface, dm : DecayInterface):
        self.manager = CMNDGenerationManager(master, dm)
        
    def add_new_particles(self, particles : list):
        """
        Add new particles to the CMND configuration.

        Args:
            particles (list): A list of new particle definitions to include.

        Returns:
            None
        """
        self.manager.add_new_particles(particles)
        
    def change_sm_particles(self, particles : List[int], file_path : Path):
        """
        Modify Standard Model particles using values from an external file.

        Args:
            particles (List[int]): A list of PDG codes representing SM particles to modify.
            file_path (Path): Path to the file containing replacement parameters.

        Returns:
            None
        """
        self.manager.change_sm_particles(particles, file_path)
    
    def add_decay_from_bsm_particles(self, mother_particle : int):
        """
        Add decay channels for a BSM (Beyond Standard Model) mother particle.

        Args:
            mother_particle (int): The PDG code of the BSM mother particle.

        Returns:
            None
        """
        self.manager.add_decay_from_bsm_particles(mother_particle)
        
    def add_decay_to_bsm_particles(self, daugther_id : int):
        """
        Add decays that produce a specified BSM daughter particle.

        Args:
            daugther_id (int): The PDG code of the BSM daughter particle.

        Returns:
            None
        """
        self.manager.add_decay_to_bsm_particles(daugther_id)
        
    def add_hard_production(self, hard_production : AbstractEnumProduction):
        """
        Define a hard production process for event generation.

        Args:
            hard_production (AbstractEnumProduction): Enum value specifying the production channel.

        Returns:
            None
        """
        self.manager.add_hard_production(hard_production)
        
    def special_change(self, spec : Specials, cases : Dict[Any, Any]):
        self.manager.add_specials_cases(spec, cases)

    def add_general_changes(self, Generaltype : GeneralType, Generalparam : GeneralParams, value):
        self.manager.add_general_changes(Generaltype, Generalparam, value)

    def serialize(self):
        """
        Serialize the current CMND configuration into a string format.

        Returns:
            str: The serialized CMND content ready for output or writing to file.
        """
        return self.manager.serialize()
    