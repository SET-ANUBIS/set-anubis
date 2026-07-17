"""Unit tests for the MadGraph application service."""

from pathlib import Path

from SetAnubis.core.MadGraph.domain.MadGraphManager import MadGraphManager


class _Runner:
    def __init__(self):
        self.run_calls = []
        self.retrieve_calls = []

    def run(self, *args):
        self.run_calls.append(args)

    def retrieve_events(self, *args):
        self.retrieve_calls.append(args)


def test_manager_forwards_cards_in_runner_order_and_retrieves_outputs(tmp_path):
    runner = _Runner()
    manager = MadGraphManager(
        runner,
        jobscript_str="generate p p > n1 n1",
        param_card_str="param",
        run_card_str="run",
        pythia_card_str="pythia",
        madspin_card_str="madspin",
    )

    manager.run()
    manager.retrieve_events(tmp_path / "events", width_mode=True)

    assert runner.run_calls == [
        ("generate p p > n1 n1", "run", "param", "pythia", "madspin")
    ]
    assert runner.retrieve_calls == [(str(tmp_path / "events"), True)]


def test_manager_accepts_optional_cards_and_default_output_directory():
    runner = _Runner()
    manager = MadGraphManager(runner, "job", "param", "run")

    manager.run()
    manager.retrieve_events()

    assert runner.run_calls == [("job", "run", "param", None, None)]
    assert runner.retrieve_calls == [("db/Temp/madgraph/Events", False)]
