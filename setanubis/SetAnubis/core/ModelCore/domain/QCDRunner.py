import numpy as np
from enum import Enum
from SetAnubis.core.ModelCore.domain import SetAnubisManager

PI = np.pi
ZETA_3 = 1.2020569031595942


class MassType(Enum):
    """
    Enum representing different types of quark masses.
    """
    RUNNING = 0
    POLE = 1


class QCDRunner:
    """
    Class for running Quantum Chromodynamics (QCD) calculations, including strong coupling constant computations 
    and quark mass running from one energy scale to another.
    """
    def __init__(self, alpha_s_MZ: float, m_Z: float, m_t_pole: float, m_b_running: float, 
                 m_u: float, m_d: float, m_s: float, m_c: float) -> None:
        self.Lambda_5 = QCDRunner.__match_lambda(alpha_s_MZ, m_Z, 5)
        self.m_t_pole = m_t_pole
        self.m_b_running = m_b_running
        self.m_u = m_u
        self.m_d = m_d
        self.m_s = m_s
        self.m_c = m_c
        self.m_t_running = 0
        self.m_b_pole = 0
        self.__set_mt_running()
        self.__set_mb_pole()
        self.__set_mass_types(MassType.POLE, MassType.POLE)

    @classmethod
    def from_manager(cls, neo: SetAnubisManager):
        """
        Alternate constructor using a SetAnubisManager instance.
        """
        alpha_s_MZ = 0.1172
        m_Z = neo.get_mass(23)
        m_t_pole = 172.5
        m_b_running = 4.25
        m_u = neo.get_mass(2)
        m_d = neo.get_mass(1)
        m_s = neo.get_mass(3)
        m_c = neo.get_mass(4)
        return cls(alpha_s_MZ, m_Z, m_t_pole, m_b_running, m_u, m_d, m_s, m_c)
        
    def alpha_s(self, Q: float, mass_b_type: MassType=None, mass_t_type: MassType=None) -> float:
        """
        Compute the strong coupling constant at a given energy scale Q.
        
        :param Q: Energy scale.
        :param mass_b_type: Type of mass for the bottom quark.
        :param mass_t_type: Type of mass for the top quark.
        :return: Strong coupling constant at energy Q.
        """
        self.__set_mass_types(mass_b_type, mass_t_type)
        n_i = 5
        n_f = self.__get_nf(Q)

        L = self.Lambda_5
        Q_bounds = self.__get_ordered_masses() 

        while n_i > n_f:
            alpha_match = QCDRunner.__eval_alpha_s(Q_bounds[n_i - 1], L, n_i)
            L = QCDRunner.__match_lambda(alpha_match, Q_bounds[n_i - 1], n_i - 1)
            n_i -= 1

        while n_i < n_f:
            alpha_match = QCDRunner.__eval_alpha_s(Q_bounds[n_i], L, n_i)
            L = QCDRunner.__match_lambda(alpha_match, Q_bounds[n_i], n_i + 1)
            n_i += 1

        return QCDRunner.__eval_alpha_s(Q, L, n_f)

    def running_mass(self, mass: float, Q_i: float, Q_f: float, mass_b_type: MassType=None, mass_t_type: MassType=None) -> float:
        """
        Compute the running quark mass from an initial energy scale to a final energy scale.
        
        :param mass: Initial quark mass.
        :param Q_i: Initial energy scale.
        :param Q_f: Final energy scale.
        :param mass_b_type: Type of mass for the bottom quark.
        :param mass_t_type: Type of mass for the top quark.
        :return: Running mass at energy Q_f.
        """
        self.__set_mass_types(mass_b_type, mass_t_type)
        n_i = self.__get_nf(Q_i)
        n_f = self.__get_nf(Q_f)
        Q_bounds = self.__get_ordered_masses() 

        while n_i > n_f:
            mass = self.__run_mass(mass, Q_i, Q_bounds[n_i - 1], n_i)
            Q_i = Q_bounds[n_i - 1]
            n_i -= 1

        while n_i < n_f:
            mass = self.__run_mass(mass, Q_i, Q_bounds[n_i], n_i)
            Q_i = Q_bounds[n_i]
            n_i += 1

        return self.__run_mass(mass, Q_i, Q_f, n_f)
    
    def __set_mass_types(self, mass_b_type: MassType, mass_t_type: MassType):
        if mass_b_type: self.m_b_type = mass_b_type
        if mass_t_type: self.m_t_type = mass_t_type

    def __get_ordered_masses(self) -> tuple[float]:
        m_b = self.m_b_pole if self.m_b_type == MassType.POLE else self.m_b_running
        m_t = self.m_t_pole if self.m_t_type == MassType.POLE else self.m_t_running
        return [self.m_u, self.m_d, self.m_s, self.m_c, m_b, m_t]


    def __run_mass(self, mass: float, Q_i: float, Q_f: float, nf: int) -> float:
        return mass * (QCDRunner.__R(self.alpha_s(Q_f), nf) / QCDRunner.__R(self.alpha_s(Q_i), nf))

    def __get_nf(self, Q: float) -> int:
        for (i, m) in enumerate(self.__get_ordered_masses()):
            if Q < m:
                return i
        return 6

    def __set_mb_pole(self) -> None:
        alpha_mb = self.alpha_s(self.m_b_running, MassType.RUNNING, MassType.POLE)
        self.m_b_pole = self.m_b_running * (1 + alpha_mb / PI * (4. / 3 
                                                                 + alpha_mb / PI * ((13.4434 - 4.1656 
                                                                                     + 1.3885 * ((self.m_u + self.m_d + self.m_s + self.m_c) / self.m_b_running)))))

    def __set_mt_running(self) -> None:
        alpha_mt = self.alpha_s(self.m_t_pole, MassType.RUNNING, MassType.POLE)
        calc_mt = lambda a_s : self.m_t_pole / (1 + a_s / 6 / PI * (8. + a_s / PI * (2053. / 48 + 2 * PI ** 2 * (1 + np.log(2) / 3) - ZETA_3)))
        self.m_t_running = calc_mt(alpha_mt)
        alpha_mt = self.alpha_s(self.m_t_running, MassType.RUNNING, MassType.RUNNING)
        self.m_t_running = calc_mt(alpha_mt)

    def __eval_alpha_s(Q: float, Lambda: float, nf: int) -> float:
        r = (Q / Lambda) ** 2
        L = np.log(r)
        LL = np.log(L)
        b0, b1, b2 = QCDRunner.__get_betas(nf)
        return 4 * PI * (1 - 2 * b1 * LL / (b0 ** 2 * L) + 4 * b1 ** 2 * ((LL - 0.5) ** 2 + b2 * b0 / 8 / b1 ** 2 - 1.25) / (b0 ** 2 * L) ** 2) / (b0 * L)
    
    def __match_lambda(target_alpha: float, Q: float, nf: int) -> float:
        f = lambda L : QCDRunner.__eval_alpha_s(Q, L, nf) - target_alpha
        L_min = 1e-3
        L_max = 1
        while np.abs(1 - L_min / L_max) > 1e-5:
            L_moy = (L_min + L_max) / 2
            if f(L_moy) > 0:
                L_max = L_moy
            else:
                L_min = L_moy

        return L_min

    def __get_betas(nf: int) -> tuple[float, float, float]:
        b0 = 11 - 2. * nf / 3
        b1 = 51 - 19. * nf / 3
        b2 = 2857 - 5033. * nf / 9 + 325. * nf ** 2 / 27
        return b0, b1, b2

    def __get_gammas(nf: int) -> tuple[float, float, float]:
        g0 = 2
        g1 = 101.0 / 12 - 5. * nf / 18
        g2 = (1249 - (2216. / 27 + 160 * ZETA_3 / 3) * nf - 140. * nf ** 2 / 81) / 32
        return g0, g1, g2
    
    def __R(alpha: float, nf: int) -> float:
        b0, b1, b2 = QCDRunner.__get_betas(nf)
        g0, g1, g2 = QCDRunner.__get_gammas(nf)
        a = (b0 * alpha / (2 * PI)) ** (2 * g0 / b0)
        b = (2 * g1 / b0 - b1 * g0 / b0 ** 2) * alpha / PI
        c = 0.5 * ((2 * g1 / b0 - b1 * g0 / b0 ** 2) ** 2 
                   + 2 * g2 / b0 - b1 * g1 / b0 ** 2 - b2 * g0 / (4 * b0) ** 2 
                   + b1 ** 2 * g0 / (2 * b0 ** 3)) * (alpha / PI) ** 2
        return a * (1 + b + c)


if __name__ == '__main__':
    runner = QCDRunner(0.1172, 91.1876, 172.5, 4.25, 2.2e-3, 4.7e-3, 0.093, 1.27)
    print(runner.running_mass(4.25, 4.25, 81, MassType.RUNNING))  # 2.96741