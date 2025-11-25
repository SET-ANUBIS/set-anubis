# tests/unit/branchingratio/test_decay_checker_unit.py
import pytest

from SetAnubis.core.BranchingRatio.domain.DecayChecker import DecayChecker

# ---- Fake NSA ----
class FakeNSA:
    """
    Simule NeoSetAnubisInterface.get_particle_info(pdg_code) en renvoyant la charge
    avec la bonne gestion du signe, comme ton manager :
      - si pdg > 0  -> charge telle que définie dans charges_pos[pdg]
      - si pdg < 0  -> charge opposée de charges_pos[abs(pdg)]
    """
    def __init__(self, charges_pos):
        # charges_pos: dict {pdg(>0): charge(particule)}
        self._c = dict(charges_pos)

    def get_particle_info(self, pdg_code):
        if pdg_code >= 0:
            ch = self._c.get(pdg_code, 0.0)
        else:
            ch = -self._c.get(abs(pdg_code), 0.0)
        return {"charge": ch}

@pytest.fixture
def checker():
    return DecayChecker()

@pytest.fixture
def nsa_std():
    # Quelques particules usuelles : 11(e-), 13(mu-), 22(γ), 23(Z)
    return FakeNSA({
        11: -1.0,  # e-
        13: -1.0,  # mu-
        22:  0.0,  # photon
        23:  0.0,  # Z
    })


def test_valid_neutral_mother_pair_leptons(checker, nsa_std):
    # Z (23, charge 0) -> e- (11) + e+ (-11)
    assert checker.check_decay_validity(23, [11, -11], nsa_std) is True

def test_valid_charged_mother_emission_neutral(checker, nsa_std):
    # e- (11, charge -1) -> e- (11) + gamma (22)
    assert checker.check_decay_validity(11, [11, 22], nsa_std) is True

def test_invalid_charge_not_conserved(checker, nsa_std):
    # Z (0) -> e- + e- (-1 + -1 = -2) => invalide
    with pytest.raises(ValueError, match="Charge not conserved"):
        checker.check_decay_validity(23, [11, 11], nsa_std)

def test_negative_mother_sign_handling(checker, nsa_std):
    # mère = -11 (e+) charge +1, filles = e- (11) + γ (0) => somme -1 : invalide
    with pytest.raises(ValueError):
        checker.check_decay_validity(-11, [11, 22], nsa_std)
