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


def _write(tmp_path, text: str, name: str = "model.py"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_parse_realistic_file_with_noise(tmp_path):
    noisy_src = '''
# du bruit
import math as m
from collections import namedtuple
SOMETHING = 42
Foo = SomethingElse(a=1, b=2)  # non supporté -> ignoré

# Objets UFO
d_quark = Particle(pdg_code=1, name='d', antiname='d~', mass=P.Md, width=0, charge='-1/3')
zwidths = Decay(name='Z', particle='Z', partial_widths=[('e-','e+'), ('mu-','mu+')])
Gf      = Parameter(name='Gf', nature='external', type='real', value=1.16639e-5)

X = 3.14  # assign simple -> ignoré
'''
    path = _write(tmp_path, noisy_src)

    objs = ufo_parser.UFOParser.parse(str(path))
    assert len(objs) == 3

    d, z, gf = objs
    assert isinstance(d, DummyParticle) and d.kwargs["pdg_code"] == 1
    assert isinstance(z, DummyDecay) and z.kwargs["name"] == "Z"
    assert isinstance(gf, DummyParameter) and gf.kwargs["name"] == "Gf"
