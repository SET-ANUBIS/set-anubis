from SetAnubis.core.Pythia.domain.cmnd_section import CMNDSection
from SetAnubis.core.Pythia.domain.cmnd_section_type import CMNDSectionType
from SetAnubis.core.Pythia.domain.cmnd_format import ParticleFormat, DecayFormat
from SetAnubis.core.Pythia.domain.hard_production_selection import HardProductionQCDList, HardProductionElectroweakList, AbstractEnumProduction
from SetAnubis.core.Pythia.adapters.YAMLReader import YamlReader
from SetAnubis.core.Pythia.domain.special_cases import Specials, GeneralParams, GeneralType
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface, Unit
from SetAnubis.core.Common.MultiSet import MultiSet
from pathlib import Path
from typing import Dict, Tuple, List, Any
import numpy as np

HBAR = 6.582*10e-25
Clight = 3*10e9

def is_convertible_to_int(val) -> bool:
    return isinstance(val, int) or (isinstance(val, str) and val.isdigit())

def is_convertible_to_float(val) -> bool:
    if isinstance(val, float) or isinstance(val, int):
        return True
    if isinstance(val, str):
        try:
            float(val)
            return True
        except ValueError:
            return False
    return False

class CMNDGenerationManager:
    def __init__(self, master : SetAnubisInterface, dm : DecayInterface):
        self.master = master
        self.decay_manager = dm
        self.config = None
        self.head = None
        self.tail = None
        self.specials : Dict[Specials,Dict[Any, Any]] = {}
        self._build_default_structure()

    def _build_default_structure(self):
        self.add_section(CMNDSectionType.HEADER, self._default_header())

    def add_section(self, section_type, content):
        section = CMNDSection(section_type, content)
        if not self.head:
            self.head = self.tail = section
        else:
            self.tail.next = section
            self.tail = section

    def add_custom_line(self, line : str):
        self.add_section(CMNDSectionType.GENERAL, line)

    def add_specials_cases(self, special : Specials, cases : Dict[Any, Any]):
        match special:
            case Specials.TAU0:
                if not (
                    isinstance(cases, dict)
                    and all(isinstance(k, int) for k in cases.keys())
                    and all(is_convertible_to_float(v) for v in cases.values())
                ):
                    raise ValueError(f"tau0 must be convertible to Dict[int, float], got: {cases}")

            case Specials.MEMODE:
                if not (
                    isinstance(cases, dict)
                    and all(isinstance(k, MultiSet) for k in cases.keys())
                    and all(is_convertible_to_int(v) for v in cases.values())
                ):
                    raise ValueError(f"memode must be convertible to Dict[MultiSet, int], got: {cases}")

        self.specials[special] = cases

    def add_general_changes(self, Generaltype : GeneralType, Generalparam : GeneralParams, value):
        self.add_section(CMNDSectionType.GENERAL, f"{Generaltype.value}:{Generalparam.value} = {value}")

    def change_tau0max(self, value : float):
        self.add_section(CMNDSectionType.GENERAL, f"ParticleDecays:tau0Max = {value} ")

    def add_new_particles(self, particles : list):
        result = ""
        for particle in particles:
            particle_info = self.master.get_all_particles()[particle]
            tau0 = self.tau0_calculation(particle)
            # tau0 = 900
            if self.specials.get(Specials.TAU0, 0) and self.specials[Specials.TAU0].get(particle):
                tau0 = self.specials[Specials.TAU0].get(particle)
            result += repr(ParticleFormat(particle, particle_info["name"], particle_info["antiname"], particle_info["spin"], int(3*particle_info["charge"]), self.charge_ufo_to_pythia(particle_info["color"]), self.master.get_particle_mass(particle).real, 0, 0, 0, tau0, False, False, True, False, True, True)) + "\n"
            # result += "9900012:doForceWidth = on\n"
            result += f"9900012:mayDecay=on\n"
            result += f"9900012:tauCalc=off\n"
            result += f"9900012:tau0={tau0}\n"
            result += f"9900012:mwidth={self.decay_manager.get_decay_tot(particle)}\n"
            # result += f"9900012:mayDecay=on\n"
            result += f"9900012:isVisible=on\n"
            print(self.decay_manager.get_decay_tot(particle))
        self.add_section(CMNDSectionType.NEW_PARTICLES, result)
        
    def change_sm_particles(self, particles : List[int], file_path : Path):
        result = ""
        data = YamlReader.get(file_path)
        for particle in particles:
            particle_info = data[particle]
            result += repr(ParticleFormat(particle, particle_info["name"], particle_info["antiname"], particle_info["spin"], particle_info["charge"], particle_info["color"], particle_info["mass"], particle_info["mWidth"], particle_info["mMin"], particle_info["mMax"], particle_info["tau0"], particle_info["tauCalc"], particle_info["isResonance"], particle_info["mayDecay"], particle_info["doExternalDecay"], particle_info["isVisible"], particle_info["doForceWidth"])) + "\n"
        self.add_section(CMNDSectionType.SM_PARTICLES_CHANGES, result)
        
    
    def add_decay_from_bsm_particles(self, decays : Dict[Tuple, Dict]):
        result = ""
        for particle, data in decays.items():
            for daugther, width in data.items():
                if abs(width) > 1e-30:
                    result += repr(DecayFormat(particle, 1, width, 0, len(daugther), [x for x in daugther]))
        self.add_section(CMNDSectionType.NEW_PARTICLES_DECAYS, result)
        
    def add_decay_from_bsm_particles(self, mother_particle : int):
        result = ""
        for daugthers in self.decay_manager.get_all_decays(mother_particle):
            br = self.decay_manager.get_br(mother_particle, daugthers)
            if abs(br) > 1e-30:
                result += repr(DecayFormat(mother_particle, 1, br, 0, len(daugthers), [x for x in daugthers])) + "\n"
        self.add_section(CMNDSectionType.NEW_PARTICLES_DECAYS, result)
        
        
    def add_decay_to_bsm_particles(self, decays : Dict[Tuple, Dict]):
        result = ""
        for particle, data in decays.items():
            for daugther, width in data.items():
                result += repr(DecayFormat(particle, 1, width, 0, len(daugther), [x for x in daugther]))
        self.add_section(CMNDSectionType.SM_PARTICLES_DECAY_TO_NEW, result)
        
    def add_decay_to_bsm_particles(self, daugther_id : int):
        result = ""
        for particle, data in self.decay_manager.get_all_decays():
            if daugther_id in data:
                result += repr(DecayFormat(particle, 1, self.decay_manager.get_br(particle, data), 0, len(data), [x for x in data])) + "\n"
        # for particle, data in decays.items():
        #     for daugther, width in data.items():
        #         result += repr(DecayFormat(particle, 1, width, 0, len(daugther), [x for x in daugther]))
        self.add_section(CMNDSectionType.SM_PARTICLES_DECAY_TO_NEW, result)
        
    def add_decay_to_sm_particles(self, decays : Dict[Tuple, Dict]):
        result = ""
        for particle, data in decays.items():
            for daugther, width in data.items():
                result += repr(DecayFormat(particle, 1, width, 0, len(daugther), [x for x in daugther]))
        self.add_section(CMNDSectionType.SM_PARTICLES_DECAY_TO_SM, result)
        
    def add_hard_production(self, hard_production : AbstractEnumProduction):
        result = hard_production.value + " = on\n" 
        self.add_section(CMNDSectionType.HARD_PRODUCTION, result)
        
    def serialize(self):
        lines = []
        current = self.head
        while current:
            lines.append(str(current))
            current = current.next
        return "\n\n".join(lines)

    @classmethod
    def deserialize(cls, text: str):
        sections = text.strip().split("\n\n")
        card = cls(config=None)  # will fix this later
        card.head = card.tail = None
        for sec in sections:
            card.add_section(CMNDSectionType.FOOTER, sec)
        return card

    def tau0_calculation(self, mother : int) -> float:
        tau0 = self.decay_manager.calculate_lifetime(mother, Unit.MM)
        if tau0 == np.inf:
            return 1e20 #TODO : handle this better
        return tau0
    
        width = self.decay_manager.get_decay_tot(mother)
        if width != 0:
            return HBAR*Clight/width * 10e3 #10e3 for mm in pythia
        else:
            return 10e5 #TODO : better
    
    def charge_ufo_to_pythia(self, ufo_charge : int) -> int:
        if ufo_charge == 1:
            return 0
        elif ufo_charge == 8:
            return 2
        elif ufo_charge == 3:
            return 1
        elif ufo_charge == -3:
            return -1
        else:
            raise ValueError(f"Not a valid charge from UFO : {ufo_charge}")
    def _default_header(self):
        return """#! 1) Settings used in the main program.
Main:numberOfEvents = 10000        ! number of events to generate
Main:timesAllowErrors = 3          ! how many aborts before run stops

! 2) Settings related to output in init(), next() and stat().
Init:showChangedSettings = on      ! list changed settings
Init:showChangedParticleData = on ! list changed particle data
Next:numberCount = 500             ! print message every n events
Next:numberShowInfo = 2            ! print event information n times
Next:numberShowProcess = 2         ! print process record n times
Next:numberShowEvent = 2           ! print event record n times

! 3) Beam parameter settings. Values below agree with default ones.
Beams:idA = 2212                   ! first beam, p = 2212, pbar = -2212
Beams:idB = 2212                   ! second beam, p = 2212, pbar = -2212
Beams:eCM = 13000.                 ! CM energy of collision"""


