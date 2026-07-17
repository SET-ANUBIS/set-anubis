"""Unit tests for MadGraph and MadSpin card domain builders."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from SetAnubis.core.MadGraph.domain.MadGraphCommandCard import MadGraphCommandCard
from SetAnubis.core.MadGraph.domain.MadGraphCommandConfig import MadGraphCommandConfig
from SetAnubis.core.MadGraph.domain.MadGraphWidthCard import MadGraphWidthCard
from SetAnubis.core.MadGraph.domain.MadspinCardBuilder import MadSpinCardBuilder
from SetAnubis.core.MadGraph.domain.MadspinSectionType import MadSpinSectionType


@dataclass
class FakeSetAnubis:
    """Provide the UFO path expected by MadGraphCommandConfig."""

    path: str = "/tmp/UFO_HNL"

    def get_ufo_path(self) -> str:
        return self.path


def test_command_card_builds_processes_scans_and_optional_cards():
    config = MadGraphCommandConfig(
        neo_set_anubis=FakeSetAnubis(),
        shower="py8",
        madspin="ON",
    )
    card = MadGraphCommandCard(config)
    card.add_define("hnl", ["n1", "n1~", " "])
    card.add_process("generate p p > n1 n1")
    card.add_process("add process p p > z")
    card.add_process("compute_widths n1")
    card.set_output_launch("run")
    card.configure_cards()
    card.add_W_parameter("WN1")
    card.add_parameter_scan("MN1", [1.0, 2.0])

    text = card.serialize()
    assert "import model UFO_HNL" in text
    assert "define hnl = n1 n1~" in text
    assert "output run" in text and "launch run" in text
    assert "pythia8_card.dat" in text and "madspin_card.dat" in text
    assert "set WN1 auto" in text
    assert "set MN1 scan:[1.0, 2.0]" in text

    with pytest.raises(ValueError, match="Alias cannot be empty"):
        card.add_define(" ", ["n1"])
    with pytest.raises(ValueError, match="Particles list cannot be empty"):
        card.add_define("empty", [])
    with pytest.raises(ValueError, match="already exists"):
        card.add_define("hnl", ["n2"])
    with pytest.raises(ValueError, match="Invalid process command"):
        card.add_process("display diagrams")
    with pytest.raises(ValueError, match="start with 'W'"):
        card.add_W_parameter("MN1")


def test_command_card_cache_and_explicit_model_variants():
    config = MadGraphCommandConfig(
        neo_set_anubis=FakeSetAnubis(),
        cache=True,
        shower="",
        madspin="",
        model_in_madgraph="custom_model",
    )
    card = MadGraphCommandCard(config)
    card.set_output_launch("cached")
    card.configure_cards()
    text = card.serialize()

    assert "import model custom_model" in text
    assert "output cached" not in text
    assert "launch cached" in text
    assert "pythia8_card.dat" not in text
    assert "madspin_card.dat" not in text


def test_madspin_builder_orders_and_clears_decay_lines():
    builder = MadSpinCardBuilder.deserialize(
        "# header\nset spinmode onshell\nlaunch\n"
    )
    builder.add_decay("decay n1 > mu+ mu-")
    text = builder.serialize().splitlines()
    assert text[-2:] == ["decay n1 > mu+ mu-", "launch"]

    builder.clear_decays()
    assert "decay n1" not in builder.serialize()

    empty = MadSpinCardBuilder()
    empty.add_section(MadSpinSectionType.LAUNCH, "launch")
    empty.add_decay("decay x > y z")
    assert empty.serialize().splitlines() == ["decay x > y z", "launch"]


def test_width_card_uses_model_directory_name():
    text = MadGraphWidthCard("/models/UFO_HNL", ["n1", "n2"]).generate()
    assert text.splitlines() == [
        "import model sm",
        "import model UFO_HNL",
        "compute_width n1",
        "compute_width n2",
    ]
