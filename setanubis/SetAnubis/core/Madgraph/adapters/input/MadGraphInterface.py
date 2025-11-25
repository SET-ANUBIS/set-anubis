from SetAnubis.core.Madgraph.ports.IMadgraphPort import IMadGraphPort
from SetAnubis.core.Madgraph.domain.MadGraphManager import MadGraphManager
from SetAnubis.core.Madgraph.ports.output.IMadGraphRunner import IMadGraphRunner

class MadgraphInterface(IMadGraphPort):
    def __init__(
        self,
        madgraph_runner: IMadGraphRunner,
        jobscript_str: str,
        param_card_str: str,
        run_card_str: str,
        pythia_card_str: str = None,
        madspin_card_str: str = None,
    ):
        self.manager = MadGraphManager(madgraph_runner, jobscript_str, param_card_str, run_card_str, pythia_card_str, madspin_card_str)
        
    def run(self) -> None:
        """
        Executes MadGraph inside the Docker container using the provided cards.
        """
        self.manager.run()
        
    def retrieve_events(self, output_path: str = "db/Temp/madgraph/Events", width_mode = False) -> None:
        """
            Copies the generated Events folder from the Docker container to the host machine.

            Args:
                output_path (str): Destination path on the host to store events.
        """
        self.manager.retrieve_events(output_path, width_mode)