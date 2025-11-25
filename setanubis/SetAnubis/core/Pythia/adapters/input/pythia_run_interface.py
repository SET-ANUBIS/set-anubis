from SetAnubis.core.Pythia.domain.pythia_run_manager import PythiaSimulationManager
from pathlib import Path
from typing import List

class PythiaRunInterface:
    """
    Interface for managing Pythia simulation runs.

    This class wraps the `PythiaSimulationManager` and exposes simplified methods 
    for directory management and executing simulations based on configuration files.

    Args:
        base_output_dir (str): Path to the base directory where outputs should be stored.
        new_particles (List[int]) : id of the new particles in the model.

    Attributes:
        manager (PythiaSimulationManager): Internal manager responsible for running simulations 
            and handling output directories.
    """
    def __init__(self, base_output_dir : str, new_particles : List[int]):
        self.manager = PythiaSimulationManager(base_output_dir, new_particles)
        
    def ensure_directories(self, sub_dirs) -> list:
        """
        Ensure that the specified subdirectories exist within the base output directory.

        Args:
            sub_dirs: A list of subdirectory names to create or validate.

        Returns:
            list: A list of absolute paths to the ensured subdirectories.
        """
        return self.manager.ensure_directories(sub_dirs)
    
    def process_file(self, config_file: str, output_lhe_dir: str, output_hepmc_dir: str, output_text_dir : str,
                     num_events: int, suffix: str = "", include_time: bool = False):
        """
        Run a Pythia simulation using a configuration file and generate event output files.

        Args:
            config_file (str): Path to the Pythia CMND configuration file.
            output_lhe_dir (str): Directory where the LHE output will be written.
            output_hepmc_dir (str): Directory where the HEPMC output will be written.
            output_hepmc_dir (str): Directory where the configuration (cross section, Widths) output will be written.
            num_events (int): Number of events to generate in the simulation.
            suffix (str, optional): Optional suffix to add to the output filenames. Defaults to "".
            include_time (bool, optional): Whether to include a timestamp in the filenames. Defaults to False.

        Returns:
            None
        """
        self.manager.process_file(config_file, output_lhe_dir, output_hepmc_dir, output_text_dir, num_events, suffix, include_time)
        
    
    def multi_run_cmnd_folder(self, cmnd_folder: str, num_events: int,
                              output_lhe_dir: str, output_hepmc_dir: str,
                              include_time: bool = False):
        """
        Run all .cmnd files in a given folder and generate LHE and HEPMC outputs.

        Args:
            cmnd_folder (str): Path to the folder containing .cmnd files.
            num_events (int): Number of events per simulation.
            output_lhe_dir (str): Directory to store LHE files.
            output_hepmc_dir (str): Directory to store HEPMC files.
            include_time (bool): Whether to include a timestamp in output filenames.
        """
        cmnd_folder = Path(cmnd_folder)
        lhe_dir, hepmc_dir = self.ensure_directories([output_lhe_dir, output_hepmc_dir])

        for cmnd_file in cmnd_folder.glob("*.cmnd"):
            suffix = cmnd_file.stem.replace("scan_", "")
            print(f"▶️ Running simulation for {cmnd_file.name} with suffix {suffix}")
            self.process_file(str(cmnd_file), lhe_dir, hepmc_dir, num_events, suffix, include_time)

        print(f"✅ All simulations done. Output in:\n  LHE: {lhe_dir}\n  HEPMC: {hepmc_dir}")