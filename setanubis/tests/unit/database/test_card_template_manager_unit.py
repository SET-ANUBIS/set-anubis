import pytest

from SetAnubis.core.DataBase.domain.MadGraphCard import CardTemplateManager, CardType

@pytest.fixture
def manager():
    return CardTemplateManager()

def test_templates_cover_all_cardtypes(manager):
    assert set(manager.templates.keys()) == set(CardType)

@pytest.mark.parametrize("card_type, must_contain", [
    (CardType.PYTHIA8, ["Pythia8", "Main:numberOfEvents", "LesHouches:setLifetime"]),
    (CardType.MADSPIN, ["MadSpin", "set spinmode none", "launch"]),
    (CardType.RUNCARD, ["MadGraph5_aMC@NLO", "run_card.dat", "nevents", "lpp1", "pt_min_pdg"]),
])
def test_each_template_non_empty_and_has_markers(manager, card_type, must_contain):
    tpl = manager.get(card_type)
    assert isinstance(tpl, str) and len(tpl) > 0
    for token in must_contain:
        assert token in tpl

def test_get_raises_for_unknown_type(manager):
    class FakeType: pass
    with pytest.raises(ValueError):
        manager.get(FakeType)
