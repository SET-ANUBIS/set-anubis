from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class PythiaConfig:
    name: str
    bsm_particles : List[int]
    bsm_decays :  Dict[int, Tuple]
    bsm_prod : Dict[int, Tuple]
    params : Dict[str, float]