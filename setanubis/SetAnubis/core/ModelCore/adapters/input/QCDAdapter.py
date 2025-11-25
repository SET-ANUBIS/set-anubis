from SetAnubis.core.ModelCore.ports.input.IQCD import IQCD
from SetAnubis.core.ModelCore.domain.QCDRunner import MassType, QCDRunner
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface

class QCDAdapter(IQCD):

    def __init__(self, qcd_runner: QCDRunner):
        self.qcd_runner = qcd_runner

    @classmethod
    def from_interface(cls, neo: SetAnubisInterface):
        qcd_runner = QCDRunner.from_manager(neo)
        return cls(qcd_runner)

    @classmethod
    def from_parameters(cls, alpha_s_MZ: float, m_Z: float, m_t_pole: float, 
                        m_b_running: float, m_u: float, m_d: float, m_s: float, m_c: float):
        qcd_runner = QCDRunner(alpha_s_MZ, m_Z, m_t_pole, m_b_running, m_u, m_d, m_s, m_c)
        return cls(qcd_runner)

    def alpha_s(self, Q: float) -> float:
        return self.qcd_runner.alpha_s(Q)
    
    def running_mass(self,  mass: float, Q_i: float, Q_f: float, mass_b_type :MassType = None, mass_t_type :MassType = None) -> float:
        return self.qcd_runner.running_mass(mass, Q_i, Q_f, mass_b_type, mass_t_type)