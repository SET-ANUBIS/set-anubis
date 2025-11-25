# tests/test_qcd_runner_integration.py
import pytest
from SetAnubis.core.ModelCore.domain.QCDRunner import QCDRunner, MassType

class FakeManager:
    """
    Fake minimaliste compatible avec QCDRunner.from_manager (get_mass uniquement).
    Les masses sont en GeV et cohérentes avec le test unitaire.
    PDG: 23=Z, 1=d, 2=u, 3=s, 4=c
    """
    def __init__(self):
        self._m = {
            23: 91.1876,   # mZ
            1: 4.7e-3,     # d
            2: 2.2e-3,     # u
            3: 0.093,      # s
            4: 1.27,       # c
        }
    def get_mass(self, pdg_code: int) -> float:
        return self._m[pdg_code]

@pytest.fixture
def runner_from_mgr():
    neo = FakeManager()
    return QCDRunner.from_manager(neo)

def test_from_manager_alpha_mz_consistency(runner_from_mgr):
    a_mz = runner_from_mgr.alpha_s(91.1876)
    assert a_mz == pytest.approx(0.1172, rel=3e-3)

def test_from_manager_running_mass_pipeline(runner_from_mgr):
    m_final = runner_from_mgr.running_mass(
        mass=4.25, Q_i=4.25, Q_f=81.0, mass_b_type=MassType.RUNNING, mass_t_type=MassType.POLE
    )
    assert m_final == pytest.approx(2.96741, rel=5e-3)
