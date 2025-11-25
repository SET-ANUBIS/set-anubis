import pathlib
import pytest

import SetAnubis.core.DataBase.adapters.UFOParser as ufo_parser


class DummyBase:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

class DummyParticle(DummyBase): pass
class DummyParameter(DummyBase): pass
class DummyDecay(DummyBase): pass


@pytest.fixture(autouse=True)
def patch_object_library(monkeypatch):
    monkeypatch.setattr(ufo_parser, "Particle", DummyParticle, raising=True)
    monkeypatch.setattr(ufo_parser, "Parameter", DummyParameter, raising=True)
    monkeypatch.setattr(ufo_parser, "Decay", DummyDecay, raising=True)


def _write(tmp_path, text: str, name: str = "ufo_objects.py"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_parse_particles_parameters_and_decays(tmp_path):
    ufo_src = '''
e_minus = Particle(pdg_code=11, name='e-', antiname='e+', mass=P.Me, width=ZeroWidth, charge='-1')
up      = Particle(pdg_code=2,  name='u',  antiname='u~', mass=P.Mu, width=0,        charge=2/3)

aEWM1   = Parameter(name='aEWM1', nature='external', type='real', value=127.9, texname='aEWM1')

Wdec    = Decay(name='W', particle='W+', partial_widths=[('e+','nu_e')])

badQ    = Particle(pdg_code=999, name='X', antiname='X~', mass=P.Mx, width=0, charge='oops')  # fallback -> 0
'''
    path = _write(tmp_path, ufo_src)

    objs = ufo_parser.UFOParser.parse(str(path))
    assert len(objs) == 5

    e_minus, up, aewm1, wdec, badq = objs

    assert isinstance(e_minus, DummyParticle)
    assert e_minus.kwargs["pdg_code"] == 11
    assert e_minus.kwargs["name"] == "e-"
    assert e_minus.kwargs["antiname"] == "e+"
    assert e_minus.kwargs["mass"] == "Me"
    assert e_minus.kwargs["width"] == 0
    assert e_minus.kwargs["charge"] == '-1'

    assert isinstance(up, DummyParticle)
    assert up.kwargs["pdg_code"] == 2
    import math
    assert up.kwargs["charge"] == pytest.approx(2/3, rel=1e-12)

    assert isinstance(aewm1, DummyParameter)
    assert aewm1.kwargs["name"] == "aEWM1"
    assert aewm1.kwargs["value"] == 127.9

    assert isinstance(wdec, DummyDecay)
    assert wdec.kwargs["name"] == "W"
    assert wdec.kwargs["particle"] == "W+"
    assert wdec.kwargs["partial_widths"] == [('e+','nu_e')]

    assert isinstance(badq, DummyParticle)
    assert badq.kwargs["charge"] == 'oops'
