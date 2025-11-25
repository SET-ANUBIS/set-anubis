import os
from datetime import datetime
from typing import List
import pythia_sim

class PythiaSimulationManager:
    """Class to manage Pythia physics simulation setup and execution.

    Attributes:
        base_output_dir (str): Base directory for simulation output files.

    Methods:
        ensure_directories(sub_dirs: list[str]) -> list[str]:
            Ensures specified directories exist within the base output directory.

        create_generator(config_file: str, lhe_output: str, hepmc_output: str, num_events: int):
            Initializes and returns a Pythia event generator.

        process_file(config_file: str, output_lhe_dir: str, output_hepmc_dir: str, num_events: int, suffix: str, include_time: bool):
            Processes a configuration file to generate events and outputs them in specified formats.
    """

    def __init__(self, base_output_dir: str, new_particles : List[int]):
        """Initializes PythiaSimulationManager with a base directory.

        Args:
            base_output_dir (str): Base output directory path.
            new_particles (List[int]) : id of the new particles in the model
        """
        self.base_output_dir = base_output_dir
        self.new_particles = new_particles

    def ensure_directories(self, sub_dirs) -> List[str]:
        """Creates directories within the base output directory if they do not already exist.

        Args:
            sub_dirs (list[str]): List of subdirectories to ensure exist.

        Returns:
            list[str]: List of full paths to the ensured directories.
        """
        paths = []
        for sub_dir in sub_dirs:
            full_path = os.path.join(self.base_output_dir, sub_dir)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
            paths.append(full_path)
        return paths

    def create_generator(self, config_file: str, lhe_output: str, hepmc_output: str, text_output : str, num_events: int):
        """Creates a Pythia event generator based on specified parameters.

        Args:
            config_file (str): Path to the configuration file for the generator.
            lhe_output (str): Path for the output LHE file.
            hepmc_output (str): Path for the output HEPMC file.
            hepmc_output (str): Path for the output txt file.
            num_events (int): Number of events to generate.

        Returns:
            Generator object configured for event generation.
        """
        return pythia_sim.create_pythia_generator(config_file, lhe_output, hepmc_output, text_output, "", num_events)

    def process_file(self, config_file: str, output_lhe_dir: str, output_hepmc_dir: str, output_text_dir : str,
                     num_events: int, suffix: str = "", include_time: bool = False):
        """Processes a configuration file and generates event outputs in specified formats.

        Args:
            config_file (str): Path to the configuration file.
            output_lhe_dir (str): Directory path to store LHE output files.
            output_hepmc_dir (str): Directory path to store HEPMC output files.
            output_hepmc_dir (str): Directory path to store txt output files.
            num_events (int): Number of events to generate.
            suffix (str, optional): Suffix to append to output filenames. Defaults to "".
            include_time (bool, optional): Whether to include timestamp in the output filename. Defaults to False.

        Returns:
            None
        """
        base_name = os.path.splitext(os.path.basename(config_file))[0]
        if include_time:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            base_name = f"{timestamp}_{base_name}"

        lhe_output = os.path.join(output_lhe_dir, f"{base_name}_{suffix}.lhe")
        hepmc_output = os.path.join(output_hepmc_dir, f"{base_name}_{suffix}.hepmc")
        txt_output = os.path.join(output_text_dir, f"{base_name}_{suffix}.txt")
        generator = self.create_generator(config_file, lhe_output, hepmc_output, txt_output, num_events)
        generator.generate_events(self.new_particles)
