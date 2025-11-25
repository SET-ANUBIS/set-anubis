import pytest
from math import isfinite

from SetAnubis.core.ModelCore.domain.QCDRunner import QCDRunner, MassType

ALPHA_S_MZ = 0.1172
MZ = 91.1876
M_T_POLE = 172.5
M_B_MSbar = 4.25
M_U, M_D, M_S, M_C = 2.2e-3, 4.7e-3, 0.093, 1.27

@pytest.fixture
def runner():
    return QCDRunner(
        alpha_s_MZ=ALPHA_S_MZ,
        m_Z=MZ,
        m_t_pole=M_T_POLE,
        m_b_running=M_B_MSbar,
        m_u=M_U, m_d=M_D, m_s=M_S, m_c=M_C
    )

def test_alpha_s_at_mz_matches_input(runner):
    a_mz = runner.alpha_s(MZ)
    assert a_mz == pytest.approx(ALPHA_S_MZ, rel=3e-3)

def test_alpha_s_monotonic_decrease(runner):
    a2 = runner.alpha_s(2.0) 
    a10 = runner.alpha_s(10.0)
    a91 = runner.alpha_s(MZ)
    assert a2 > a10 > a91 > 0.0

def test_alpha_s_continuity_across_mb_threshold_running_mass(runner):
    eps = 1e-3
    Q_bm = M_B_MSbar * (1 - eps)
    Q_bp = M_B_MSbar * (1 + eps)
    a_minus = runner.alpha_s(Q_bm, mass_b_type=MassType.RUNNING, mass_t_type=MassType.POLE)
    a_plus  = runner.alpha_s(Q_bp, mass_b_type=MassType.RUNNING, mass_t_type=MassType.POLE)
    assert a_minus == pytest.approx(a_plus, abs=5e-3)

def test_running_mass_reference_number(runner):
    m_final = runner.running_mass(
        mass=4.25, Q_i=4.25, Q_f=81.0, mass_b_type=MassType.RUNNING, mass_t_type=MassType.POLE
    )
    assert m_final == pytest.approx(2.96741, rel=5e-3)

def test_internal_derived_masses_defined(runner):
    assert isfinite(runner.m_b_pole) and runner.m_b_pole > 0
    assert isfinite(runner.m_t_running) and runner.m_t_running > 0
