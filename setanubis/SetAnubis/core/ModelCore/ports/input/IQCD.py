from abc import ABC, abstractmethod

class IQCD(ABC):
    @abstractmethod
    def alpha_s(self, Q: float) -> float: ...
    
    @abstractmethod
    def running_mass(self,  mass: float, Q_i: float, Q_f: float, mass_b_type = None, mass_t_type = None): ...