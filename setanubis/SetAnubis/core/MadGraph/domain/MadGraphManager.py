"""Application service coordinating prepared cards with a MadGraph runner."""

from __future__ import annotations

from pathlib import Path

from SetAnubis.core.MadGraph.ports.output.IMadGraphRunner import IMadGraphRunner


class MadGraphManager:
    """Forward prepared MadGraph inputs to a configured execution backend."""

    def __init__(
        self,
        madgraph_runner: IMadGraphRunner,
        jobscript_str: str,
        param_card_str: str,
        run_card_str: str,
        pythia_card_str: str | None = None,
        madspin_card_str: str | None = None,
    ) -> None:
        """Store the runner and card contents used by subsequent operations."""
        self.jobscript = jobscript_str
        self.param_card = param_card_str
        self.run_card = run_card_str
        self.pythia_card = pythia_card_str
        self.madspin_card = madspin_card_str
        self.madgraph_runner = madgraph_runner

    def run(self) -> None:
        """Execute MadGraph with the stored job script and cards."""
        self.madgraph_runner.run(
            self.jobscript,
            self.run_card,
            self.param_card,
            self.pythia_card,
            self.madspin_card,
        )

    def retrieve_events(
        self,
        output_dir: str | Path = "db/Temp/madgraph/Events",
        width_mode: bool = False,
    ) -> None:
        """Ask the runner to copy generated events or width results."""
        self.madgraph_runner.retrieve_events(str(output_dir), width_mode)
