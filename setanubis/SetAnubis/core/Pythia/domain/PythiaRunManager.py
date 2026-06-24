import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import pythia_sim


class PythiaSimulationManager:
    """Manage Pythia physics simulation setup and execution.

    The manager keeps the old API intact, but now lets callers configure arbitrary
    Pythia settings, particle lifetimes / widths, and event-level hard cuts for
    any PDG id instead of assuming a single HNL PID.
    """

    def __init__(
        self,
        base_output_dir: str,
        new_particles: Optional[List[int]] = None,
        *,
        pythia_settings: Optional[List[str]] = None,
        lifetimes: Optional[Dict[int, float]] = None,
        widths: Optional[Dict[int, float]] = None,
        hard_cuts: Optional[List[Any]] = None,
        require_all_cuts: bool = True,
        max_trials: int = 1_000_000,
        fix_decay_masses: bool = True,
    ):
        self.base_output_dir = base_output_dir
        self.new_particles = [int(p) for p in (new_particles or [])]
        self.pythia_settings = list(pythia_settings or [])
        self.lifetimes = {int(k): float(v) for k, v in (lifetimes or {}).items()}
        self.widths = {int(k): float(v) for k, v in (widths or {}).items()}
        self.hard_cuts = list(hard_cuts or [])
        self.require_all_cuts = require_all_cuts
        self.max_trials = int(max_trials)
        self.fix_decay_masses = fix_decay_masses

    def ensure_directories(self, sub_dirs) -> List[str]:
        """Create directories within the base output directory if needed."""
        paths = []
        for sub_dir in sub_dirs:
            full_path = os.path.join(self.base_output_dir, sub_dir)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
            paths.append(full_path)
        return paths

    def add_pythia_setting(self, setting: str):
        """Add a raw Pythia setting applied after the CMND file is read."""
        self.pythia_settings.append(setting)

    def set_lifetime(self, particle: int, tau0_mm: float):
        """Override tau0 in mm for any particle at runtime."""
        self.lifetimes[int(particle)] = float(tau0_mm)

    def set_width(self, particle: int, width_gev: float):
        """Override mWidth in GeV for any particle at runtime."""
        self.widths[int(particle)] = float(width_gev)

    def add_hard_cut(self, cut: Any = None, **kwargs):
        """Add an event-level hard cut.

        Accepts either a pythia_sim.ParticleHardCut object, a dict, or keyword
        arguments such as pdg_id=9900012, min_pt=30, final_only=True.
        """
        if cut is None:
            cut = kwargs
        elif kwargs:
            if isinstance(cut, dict):
                cut = {**cut, **kwargs}
            else:
                for key, value in kwargs.items():
                    setattr(cut, key, value)
        self.hard_cuts.append(cut)

    def clear_hard_cuts(self):
        self.hard_cuts.clear()

    def _to_cpp_cut(self, cut: Any):
        if isinstance(cut, pythia_sim.ParticleHardCut):
            return cut

        if not isinstance(cut, dict):
            return cut

        cpp_cut = pythia_sim.ParticleHardCut()
        field_map = {
            "pdg_id": "pdg_id",
            "pdgId": "pdg_id",
            "pid": "pdg_id",
            "particle": "pdg_id",
            "use_abs_id": "use_abs_id",
            "useAbsId": "use_abs_id",
            "final_only": "final_only",
            "finalOnly": "final_only",
            "min_pt": "min_pt",
            "pt_min": "min_pt",
            "minPt": "min_pt",
            "max_pt": "max_pt",
            "pt_max": "max_pt",
            "maxPt": "max_pt",
            "min_eta": "min_eta",
            "eta_min": "min_eta",
            "minEta": "min_eta",
            "max_eta": "max_eta",
            "eta_max": "max_eta",
            "maxEta": "max_eta",
            "min_energy": "min_energy",
            "energy_min": "min_energy",
            "minEnergy": "min_energy",
            "max_energy": "max_energy",
            "energy_max": "max_energy",
            "maxEnergy": "max_energy",
            "min_count": "min_count",
            "minCount": "min_count",
            "max_count": "max_count",
            "maxCount": "max_count",
        }
        for key, value in cut.items():
            attr = field_map.get(key, key)
            if hasattr(cpp_cut, attr):
                setattr(cpp_cut, attr, value)
            else:
                raise ValueError(f"Unknown ParticleHardCut option: {key}")
        return cpp_cut

    def _build_run_options(self):
        options = pythia_sim.PythiaRunOptions()
        options.settings = list(self.pythia_settings)
        options.lifetimes = dict(self.lifetimes)
        options.widths = dict(self.widths)
        options.hard_cuts = [self._to_cpp_cut(cut) for cut in self.hard_cuts]
        options.require_all_cuts = bool(self.require_all_cuts)
        options.max_trials = int(self.max_trials)
        options.fix_decay_masses = bool(self.fix_decay_masses)
        return options

    def create_generator(self, config_file: str, lhe_output: str, hepmc_output: str, text_output: str, num_events: int):
        """Create a Pythia event generator based on specified parameters."""
        return pythia_sim.create_pythia_generator(
            config_file, lhe_output, hepmc_output, text_output, "", num_events
        )

    def process_file(
        self,
        config_file: str,
        output_lhe_dir: str,
        output_hepmc_dir: str,
        output_text_dir: str,
        num_events: int,
        suffix: str = "",
        include_time: bool = False,
        *,
        particle_ids: Optional[List[int]] = None,
        pythia_settings: Optional[List[str]] = None,
        lifetimes: Optional[Dict[int, float]] = None,
        widths: Optional[Dict[int, float]] = None,
        hard_cuts: Optional[List[Any]] = None,
        require_all_cuts: Optional[bool] = None,
        max_trials: Optional[int] = None,
        fix_decay_masses: Optional[bool] = None,
    ):
        """Run one CMND file and generate LHE, HepMC and text-summary outputs."""
        base_name = os.path.splitext(os.path.basename(config_file))[0]
        if include_time:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            base_name = f"{timestamp}_{base_name}"

        lhe_output = os.path.join(output_lhe_dir, f"{base_name}_{suffix}.lhe")
        hepmc_output = os.path.join(output_hepmc_dir, f"{base_name}_{suffix}.hepmc")
        txt_output = os.path.join(output_text_dir, f"{base_name}_{suffix}.txt")

        generator = self.create_generator(config_file, lhe_output, hepmc_output, txt_output, num_events)

        old_state = (
            list(self.pythia_settings),
            dict(self.lifetimes),
            dict(self.widths),
            list(self.hard_cuts),
            self.require_all_cuts,
            self.max_trials,
            self.fix_decay_masses,
        )
        try:
            if pythia_settings:
                self.pythia_settings.extend(pythia_settings)
            if lifetimes:
                self.lifetimes.update({int(k): float(v) for k, v in lifetimes.items()})
            if widths:
                self.widths.update({int(k): float(v) for k, v in widths.items()})
            if hard_cuts is not None:
                self.hard_cuts = list(hard_cuts)
            if require_all_cuts is not None:
                self.require_all_cuts = bool(require_all_cuts)
            if max_trials is not None:
                self.max_trials = int(max_trials)
            if fix_decay_masses is not None:
                self.fix_decay_masses = bool(fix_decay_masses)

            options = self._build_run_options()
            generator.generate_events(particle_ids or self.new_particles, options)
        finally:
            (
                self.pythia_settings,
                self.lifetimes,
                self.widths,
                self.hard_cuts,
                self.require_all_cuts,
                self.max_trials,
                self.fix_decay_masses,
            ) = old_state
