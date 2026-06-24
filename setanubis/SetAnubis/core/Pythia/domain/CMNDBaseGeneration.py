from __future__ import annotations
from SetAnubis.core.Pythia.domain.CMNDSection import CMNDSection
from SetAnubis.core.Pythia.domain.CMNDSectionType import CMNDSectionType
from SetAnubis.core.Pythia.domain.CMNDFormat import ParticleFormat, DecayFormat
from SetAnubis.core.Pythia.domain.HardProductionSelection import AbstractEnumProduction
from SetAnubis.core.Pythia.adapters.YAMLReader import YamlReader
from SetAnubis.core.Pythia.domain.SpecialCases import Specials, GeneralParams, GeneralType
from SetAnubis.core.Common.MultiSet import MultiSet
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union
import numpy as np

if TYPE_CHECKING:
    from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface
    from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface

HBAR = 6.582e-25
Clight = 3e11  # mm / s


def is_convertible_to_int(val) -> bool:
    return isinstance(val, int) or (isinstance(val, str) and val.isdigit())


def is_convertible_to_float(val) -> bool:
    if isinstance(val, (float, int)):
        return True
    if isinstance(val, str):
        try:
            float(val)
            return True
        except ValueError:
            return False
    return False


def pythia_bool(value: bool) -> str:
    return "on" if bool(value) else "off"


class CMNDGenerationManager:
    def __init__(self, master: SetAnubisInterface, dm: DecayInterface):
        self.master = master
        self.decay_manager = dm
        self.config = None
        self.head = None
        self.tail = None
        self.specials: Dict[Specials, Dict[Any, Any]] = {}
        self.particle_options: Dict[int, Dict[str, Any]] = {}
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

    def add_custom_line(self, line: str):
        self.add_section(CMNDSectionType.GENERAL, line)

    def add_pythia_setting(self, key: str, value: Any = None):
        """Add an arbitrary Pythia setting to the CMND card.

        Examples:
            add_pythia_setting("PhaseSpace:pTHatMin", 20)
            add_pythia_setting("HardQCD:hardbbbar", "on")
            add_pythia_setting("WeakSingleBoson:all = on")
        """
        if value is None:
            self.add_section(CMNDSectionType.GENERAL, str(key))
        else:
            self.add_section(CMNDSectionType.GENERAL, f"{key} = {value}")

    def add_specials_cases(self, special: Specials, cases: Dict[Any, Any]):
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

    def add_general_changes(self, Generaltype: Union[GeneralType, str], Generalparam: Union[GeneralParams, str], value):
        general_type = Generaltype.value if isinstance(Generaltype, GeneralType) else str(Generaltype)
        general_param = Generalparam.value if isinstance(Generalparam, GeneralParams) else str(Generalparam)
        self.add_section(CMNDSectionType.GENERAL, f"{general_type}:{general_param} = {value}")

    def change_tau0max(self, value: float):
        self.add_section(CMNDSectionType.GENERAL, f"ParticleDecays:tau0Max = {value}")

    def set_particle_options(self, particle: int, **options):
        """Override Pythia particle-data options for one particle.

        Supported keys include: tau0, tauCalc, mWidth, mMin, mMax, isResonance,
        mayDecay, doExternalDecay, isVisible, doForceWidth, and extra_settings.
        The extra_settings dict is rendered as '<pid>:<key> = <value>'.
        """
        current = self.particle_options.setdefault(int(particle), {})
        current.update({k: v for k, v in options.items() if v is not None})

    def set_particle_lifetime(self, particle: int, tau0_mm: float):
        self.set_particle_options(particle, tau0=float(tau0_mm), tauCalc=False)

    def add_particle_setting(self, particle: int, key: str, value: Any):
        current = self.particle_options.setdefault(int(particle), {})
        extra = current.setdefault("extra_settings", {})
        extra[key] = value

    def _get_particle_info(self, particle: int) -> Dict[str, Any]:
        try:
            particles = self.master.get_all_particles()
            if isinstance(particles, dict):
                return particles[particle]
        except Exception:
            pass
        return self.master.get_particle_info(particle)

    def _get_decay_width(self, particle: int) -> float:
        try:
            return float(self.decay_manager.get_decay_tot(particle))
        except Exception:
            return 0.0

    def _particle_option(self, particle: int, key: str, default: Any) -> Any:
        return self.particle_options.get(particle, {}).get(key, default)

    def _render_particle_runtime_settings(self, particle: int, tau0: float, width: float) -> str:
        options = self.particle_options.get(particle, {})
        may_decay = bool(options.get("mayDecay", True))
        tau_calc = bool(options.get("tauCalc", False))
        is_visible = bool(options.get("isVisible", True))
        do_force_width = bool(options.get("doForceWidth", True))

        lines = [
            f"{particle}:mayDecay = {pythia_bool(may_decay)}",
            f"{particle}:tauCalc = {pythia_bool(tau_calc)}",
            f"{particle}:tau0 = {tau0}",
            f"{particle}:mWidth = {width}",
            f"{particle}:isVisible = {pythia_bool(is_visible)}",
            f"{particle}:doForceWidth = {pythia_bool(do_force_width)}",
        ]

        for key, value in options.get("extra_settings", {}).items():
            lines.append(f"{particle}:{key} = {value}")
        return "\n".join(lines) + "\n"

    def add_new_particles(self, particles: list, options: Optional[Dict[int, Dict[str, Any]]] = None):
        if options:
            for particle, particle_options in options.items():
                self.set_particle_options(int(particle), **particle_options)

        result = ""
        for particle in particles:
            particle = int(particle)
            particle_info = self._get_particle_info(particle)
            tau0 = self.tau0_calculation(particle)
            if self.specials.get(Specials.TAU0, 0) and self.specials[Specials.TAU0].get(particle) is not None:
                tau0 = float(self.specials[Specials.TAU0][particle])
            tau0 = float(self._particle_option(particle, "tau0", tau0))

            width = float(self._particle_option(particle, "mWidth", self._get_decay_width(particle)))
            m_min = float(self._particle_option(particle, "mMin", 0.0))
            m_max = float(self._particle_option(particle, "mMax", 0.0))
            tau_calc = bool(self._particle_option(particle, "tauCalc", False))
            is_resonance = bool(self._particle_option(particle, "isResonance", False))
            may_decay = bool(self._particle_option(particle, "mayDecay", True))
            do_external_decay = bool(self._particle_option(particle, "doExternalDecay", False))
            is_visible = bool(self._particle_option(particle, "isVisible", True))
            do_force_width = bool(self._particle_option(particle, "doForceWidth", True))

            result += repr(ParticleFormat(
                particle,
                particle_info["name"],
                particle_info["antiname"],
                particle_info["spin"],
                int(3 * particle_info["charge"]),
                self.charge_ufo_to_pythia(particle_info["color"]),
                self.master.get_particle_mass(particle).real,
                width,
                m_min,
                m_max,
                tau0,
                tau_calc,
                is_resonance,
                may_decay,
                do_external_decay,
                is_visible,
                do_force_width,
            )) + "\n"
            result += self._render_particle_runtime_settings(particle, tau0, width)
        self.add_section(CMNDSectionType.NEW_PARTICLES, result)

    def change_sm_particles(self, particles: List[int], file_path: Path):
        result = ""
        data = YamlReader.get(file_path)
        for particle in particles:
            particle_info = data[particle]
            result += repr(ParticleFormat(
                particle,
                particle_info["name"],
                particle_info["antiname"],
                particle_info["spin"],
                particle_info["charge"],
                particle_info["color"],
                particle_info["mass"],
                particle_info["mWidth"],
                particle_info["mMin"],
                particle_info["mMax"],
                particle_info["tau0"],
                particle_info["tauCalc"],
                particle_info["isResonance"],
                particle_info["mayDecay"],
                particle_info["doExternalDecay"],
                particle_info["isVisible"],
                particle_info["doForceWidth"],
            )) + "\n"
        self.add_section(CMNDSectionType.SM_PARTICLES_CHANGES, result)

    def add_decay_from_bsm_particles(self, mother_particle: Union[int, Dict[Tuple, Dict]]):
        result = ""
        if isinstance(mother_particle, dict):
            for particle, data in mother_particle.items():
                for daughters, width in data.items():
                    if abs(width) > 1e-30:
                        result += repr(DecayFormat(particle, 1, width, 0, len(daughters), [x for x in daughters])) + "\n"
        else:
            mother_particle = int(mother_particle)
            for daughters in self.decay_manager.get_all_decays(mother_particle):
                br = self.decay_manager.get_br(mother_particle, daughters)
                if abs(br) > 1e-30:
                    me_mode = 0
                    if self.specials.get(Specials.MEMODE, 0) and self.specials[Specials.MEMODE].get(daughters) is not None:
                        me_mode = int(self.specials[Specials.MEMODE][daughters])
                    result += repr(DecayFormat(mother_particle, 1, br, me_mode, len(daughters), [x for x in daughters])) + "\n"
        self.add_section(CMNDSectionType.NEW_PARTICLES_DECAYS, result)

    def add_decay_to_bsm_particles(self, daughter_id: Union[int, Dict[Tuple, Dict]]):
        result = ""
        if isinstance(daughter_id, dict):
            for particle, data in daughter_id.items():
                for daughters, width in data.items():
                    result += repr(DecayFormat(particle, 1, width, 0, len(daughters), [x for x in daughters])) + "\n"
        else:
            daughter_id = int(daughter_id)
            for particle, daughters in self.decay_manager.get_all_decays():
                if daughter_id in daughters:
                    result += repr(DecayFormat(
                        particle,
                        1,
                        self.decay_manager.get_br(particle, daughters),
                        0,
                        len(daughters),
                        [x for x in daughters],
                    )) + "\n"
        self.add_section(CMNDSectionType.SM_PARTICLES_DECAY_TO_NEW, result)

    def add_decay_to_sm_particles(self, decays: Dict[Tuple, Dict]):
        result = ""
        for particle, data in decays.items():
            for daughters, width in data.items():
                result += repr(DecayFormat(particle, 1, width, 0, len(daughters), [x for x in daughters])) + "\n"
        self.add_section(CMNDSectionType.SM_PARTICLES_DECAY_TO_SM, result)

    def add_hard_production(self, hard_production: Union[AbstractEnumProduction, str], enabled: Any = "on"):
        setting = hard_production.value if isinstance(hard_production, AbstractEnumProduction) else str(hard_production)
        if "=" in setting:
            result = setting + "\n"
        else:
            result = f"{setting} = {enabled}\n"
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

    def tau0_calculation(self, mother: int) -> float:
        try:
            from SetAnubis.core.BranchingRatio.domain.BranchingRatioManager import Unit
            unit = Unit.MM
        except Exception:
            unit = "MM"

        try:
            tau0 = self.decay_manager.calculate_lifetime(mother, unit)
        except Exception:
            tau0 = np.inf
        if tau0 == np.inf:
            return 1e20
        return tau0

    def charge_ufo_to_pythia(self, ufo_charge: int) -> int:
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


