from typing import Dict, Any, Set, List
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation

class IFileInterpolationSubStrategy:
    """
    Interface pour lire un fichier (CSV, JSON, etc.) et 
    interpoler la valeur de la largeur partielle.
    """
    def load_file(self, file_path: str, varying_params: List[str]):
        pass

    def interpolate(self, mother: int, daughters: Set[int], param_values: Dict[str, float]) -> float:
        pass
