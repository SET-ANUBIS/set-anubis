import re
import pytest

from SetAnubis.core.DataBase.domain.MadGraphCard import CardTemplateManager, CardType

@pytest.fixture
def manager():
    return CardTemplateManager()

def _fill_runcard_template(manager,
                           pt_min="{'default': 20.0}",
                           pt_max="{'default': -1.0}",
                           eta_min="{'default': -2.5}",
                           eta_max="{'default': 2.5}",
                           mxx_min="{'default': 10.0}"):
    tpl = manager.get(CardType.RUNCARD)

    safe_tpl = tpl.replace("{'default': False}", "{{'default': False}}")

    filled = safe_tpl.format(pt_min, pt_max, eta_min, eta_max, mxx_min)
    return filled

def test_runcard_can_be_filled_with_user_cuts(manager):
    rendered = _fill_runcard_template(manager)

    assert "{'default': 20.0} = pt_min_pdg" in re.sub(r"\s+", " ", rendered)
    assert "{'default': -1.0} = pt_max_pdg" in re.sub(r"\s+", " ", rendered)
    assert "{'default': -2.5} = eta_min_pdg" in re.sub(r"\s+", " ", rendered)
    assert "{'default': 2.5} = eta_max_pdg" in re.sub(r"\s+", " ", rendered)
    assert "{'default': 10.0} = mxx_min_pdg" in re.sub(r"\s+", " ", rendered)

    assert "{'default': False} = mxx_only_part_antipart" in rendered

def test_full_roundtrip_write_to_file(tmp_path, manager):
    rendered = _fill_runcard_template(
        manager,
        pt_min="{'default': 30.0}",
        mxx_min="{'default': 25.0}",
    )
    out = tmp_path / "run_card.dat"
    out.write_text(rendered, encoding="utf-8")

    data = out.read_text(encoding="utf-8")
    assert "run_card.dat MadEvent" in data
    assert "{'default': 30.0} = pt_min_pdg" in re.sub(r"\s+", " ", data)
    assert "{'default': 25.0} = mxx_min_pdg" in re.sub(r"\s+", " ", data)

def test_other_templates_are_pass_through_strings(manager):
    p8 = manager.get(CardType.PYTHIA8)
    ms = manager.get(CardType.MADSPIN)
    assert "Pythia8" in p8 and "Main:numberOfEvents" in p8
    assert "MadSpin" in ms and "set spinmode none" in ms and "launch" in ms
