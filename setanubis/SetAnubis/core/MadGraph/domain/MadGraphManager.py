import os
import docker
import subprocess
from SetAnubis.core.MadGraph.ports.output.IMadGraphRunner import IMadGraphRunner

class MadGraphManager:
    """Class to manage MadGraph simulations using Docker containers.

    Responsible for container management, injecting simulation configuration files,
    executing MadGraph commands, and retrieving simulation results.

    Attributes:
        jobscript (str): Content of the job script for MadGraph.
        param_card (str): Content of the parameter card.
        run_card (str): Content of the run card.
        pythia_card (str, optional): Content of the Pythia8 configuration card. Defaults to None.
        madspin_card (str, optional): Content of the MadSpin configuration card. Defaults to None.
        docker_client: Docker client instance for container management.
    """
    
    def __init__(self, madgraph_runner : IMadGraphRunner, jobscript_str : str, param_card_str : str, run_card_str : str, pythia_card_str : str =None, madspin_card_str : str =None):
        """Initializes the MadGraphManager with card contents and sets up Docker.

        Args:
            jobscript_str (str): Job script content.
            param_card_str (str): Parameter card content.
            run_card_str (str): Run card content.
            pythia_card_str (str, optional): Pythia card content. Defaults to None.
            madspin_card_str (str, optional): MadSpin card content. Defaults to None.
        """
        self.jobscript = jobscript_str
        self.param_card = param_card_str
        self.run_card = run_card_str
        self.pythia_card = pythia_card_str
        self.madspin_card = madspin_card_str
        self.madgraph_runner = madgraph_runner
    

    def run(self):
        self.madgraph_runner.run(self.jobscript, self.run_card, self.param_card, self.pythia_card, self.madspin_card)

    def retrieve_events(self, output_dir="db/Temp/madgraph/Events", width_mode = False):
        self.madgraph_runner.retrieve_events(output_dir, width_mode)
