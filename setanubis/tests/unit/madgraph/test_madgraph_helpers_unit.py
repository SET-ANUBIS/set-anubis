"""Unit tests for lightweight MadGraph helpers that do not run MadGraph."""

from __future__ import annotations

from SetAnubis.core.MadGraph.adapters.input.MadGraphHepmcAnalyzer import ParticleStats
from SetAnubis.core.MadGraph.adapters.output.MadGraphLocalRunner import MadGraphLocalRunner
from SetAnubis.core.MadGraph.domain.MadGraphRunCardEditor import RunCardEditor


def test_particle_stats_summary_is_headless_and_silent(capsys):
    stats = ParticleStats(pdg_id=9900012)
    stats.register_event(has_particle=True, event_momentum_unit="GEV")
    stats.energies.extend([2.0, 4.0])
    stats.pts.extend([1.0, 3.0])
    stats.etas.extend([0.1, -0.1])
    stats.phis.extend([0.2, -0.2])
    stats.thetas.extend([1.0, 2.0])
    stats.n_particles = 2

    summary = stats.summary()

    assert "PDG 9900012" in summary
    assert "Momentum Unit" in summary
    assert capsys.readouterr().out == ""


def test_run_card_editor_updates_and_round_trips(tmp_path):
    editor = RunCardEditor("10 = nevents ! event count\n1 = iseed")
    assert editor.get("nevents") == "10"

    editor.set("nevents", 25)
    editor.set("ebeam1", 6800)
    output = tmp_path / "run_card.dat"
    editor.to_file(output)

    loaded = RunCardEditor.from_file(output)
    assert loaded.get("nevents") == "25"
    assert loaded.get("ebeam1") == "6800"
    assert set(loaded.keys()) == {"nevents", "iseed", "ebeam1"}


def test_local_runner_writes_each_card_to_the_correct_file(tmp_path):
    mg_root = tmp_path / "mg5"
    (mg_root / "bin").mkdir(parents=True)
    (mg_root / "bin" / "mg5_aMC").write_text("#!/bin/sh\n", encoding="utf-8")
    for relative in (
        "HEPTools/pythia8",
        "HEPTools/lhapdf6_py3",
        "HEPTools/MG5aMC_PY8_interface",
    ):
        (mg_root / relative).mkdir(parents=True)

    runner = MadGraphLocalRunner(madgraph_path=str(mg_root))
    cards = tmp_path / "cards"
    runner._MadGraphLocalRunner__card_path = lambda: str(cards)

    runner.inject_all_cards(
        "launch /old/param_card.dat /old/run_card.dat",
        "RUN-CARD",
        "PARAM-CARD",
        "PYTHIA-CARD",
        "MADSPIN-CARD",
    )

    assert (cards / "param_card.dat").read_text(encoding="utf-8") == "PARAM-CARD"
    assert (cards / "run_card.dat").read_text(encoding="utf-8") == "RUN-CARD"
    assert (cards / "pythia8_card.dat").read_text(encoding="utf-8") == "PYTHIA-CARD"
    assert (cards / "madspin_card.dat").read_text(encoding="utf-8") == "MADSPIN-CARD"
    job = (cards / "jobscript_param_scan.txt").read_text(encoding="utf-8")
    assert str(cards / "param_card.dat") in job
    assert str(cards / "run_card.dat") in job
