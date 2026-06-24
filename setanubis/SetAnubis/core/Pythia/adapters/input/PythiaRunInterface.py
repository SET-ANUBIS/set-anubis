from SetAnubis.core.Pythia.domain.PythiaRunManager import PythiaSimulationManager
from pathlib import Path
from typing import Any, Dict, List, Optional


class PythiaRunInterface:
    """
    Interface for managing Pythia simulation runs.

    Args:
        base_output_dir (str): Path to the base directory where outputs should be stored.
        new_particles (List[int]): PDG ids to track in summaries / decay repair.
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
        self.manager = PythiaSimulationManager(
            base_output_dir,
            new_particles or [],
            pythia_settings=pythia_settings,
            lifetimes=lifetimes,
            widths=widths,
            hard_cuts=hard_cuts,
            require_all_cuts=require_all_cuts,
            max_trials=max_trials,
            fix_decay_masses=fix_decay_masses,
        )

    def ensure_directories(self, sub_dirs) -> list:
        return self.manager.ensure_directories(sub_dirs)

    def add_pythia_setting(self, setting: str):
        self.manager.add_pythia_setting(setting)

    def set_lifetime(self, particle: int, tau0_mm: float):
        self.manager.set_lifetime(particle, tau0_mm)

    def set_width(self, particle: int, width_gev: float):
        self.manager.set_width(particle, width_gev)

    def add_hard_cut(self, cut: Any = None, **kwargs):
        self.manager.add_hard_cut(cut, **kwargs)

    def clear_hard_cuts(self):
        self.manager.clear_hard_cuts()

    def process_file(
        self,
        config_file: str,
        output_lhe_dir: str,
        output_hepmc_dir: str,
        output_text_dir: str,
        num_events: int,
        suffix: str = "",
        include_time: bool = False,
        **run_options,
    ):
        """Run a Pythia simulation using a CMND configuration file."""
        self.manager.process_file(
            config_file,
            output_lhe_dir,
            output_hepmc_dir,
            output_text_dir,
            num_events,
            suffix,
            include_time,
            **run_options,
        )

    def multi_run_cmnd_folder(
        self,
        cmnd_folder: str,
        num_events: int,
        output_lhe_dir: str,
        output_hepmc_dir: str,
        output_text_dir: str,
        include_time: bool = False,
        **run_options,
    ):
        """Run all .cmnd files in a folder and generate LHE/HEPMC/text outputs."""
        cmnd_folder = Path(cmnd_folder)
        lhe_dir, hepmc_dir, text_dir = self.ensure_directories([
            output_lhe_dir,
            output_hepmc_dir,
            output_text_dir,
        ])

        for cmnd_file in cmnd_folder.glob("*.cmnd"):
            suffix = cmnd_file.stem.replace("scan_", "")
            print(f"▶️ Running simulation for {cmnd_file.name} with suffix {suffix}")
            self.process_file(
                str(cmnd_file),
                lhe_dir,
                hepmc_dir,
                text_dir,
                num_events,
                suffix,
                include_time,
                **run_options,
            )

        print(f" All simulations done. Output in:\n  LHE: {lhe_dir}\n  HEPMC: {hepmc_dir}\n  TEXT: {text_dir}")
