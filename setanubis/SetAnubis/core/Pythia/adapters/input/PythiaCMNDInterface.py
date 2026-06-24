from __future__ import annotations
from SetAnubis.core.Pythia.domain.CMNDBaseGeneration import CMNDGenerationManager
from SetAnubis.core.Pythia.infrastructure.enums import AbstractEnumProduction
from SetAnubis.core.Pythia.domain.SpecialCases import Specials, GeneralParams, GeneralType

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface
    from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface


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
        
    def add_new_particles(self, particles : list, options: Dict[int, Dict[str, Any]] | None = None):
        """
        Add new particles to the CMND configuration.

        Args:
            particles (list): A list of PDG ids to include.
            options (dict, optional): Per-particle Pythia overrides keyed by PDG id.
                Supported keys include tau0, tauCalc, mWidth, mMin, mMax,
                isResonance, mayDecay, doExternalDecay, isVisible,
                doForceWidth, and extra_settings.

        Returns:
            None
        """
        self.manager.add_new_particles(particles, options=options)

    def set_particle_options(self, particle: int, **options):
        """Set Pythia particle-data options for any PDG id before add_new_particles()."""
        self.manager.set_particle_options(particle, **options)

    def set_particle_lifetime(self, particle: int, tau0_mm: float):
        """Set a forced proper lifetime tau0 in mm for any PDG id."""
        self.manager.set_particle_lifetime(particle, tau0_mm)

    def add_particle_setting(self, particle: int, key: str, value: Any):
        """Add a raw '<pid>:<key> = <value>' setting for one particle."""
        self.manager.add_particle_setting(particle, key, value)

    def add_pythia_setting(self, key: str, value: Any = None):
        """Add an arbitrary Pythia setting, e.g. 'PhaseSpace:pTHatMin = 20'."""
        self.manager.add_pythia_setting(key, value)
        
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
        
    def add_hard_production(self, hard_production : AbstractEnumProduction | str, enabled: Any = "on"):
        """
        Define a hard production process for event generation.

        Args:
            hard_production: Enum value or raw Pythia setting name.
            enabled: Value written after '=' when hard_production is not already a full assignment.

        Returns:
            None
        """
        self.manager.add_hard_production(hard_production, enabled)
        
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
    