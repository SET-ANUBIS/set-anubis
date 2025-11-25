# ===========================
# Fichier : my_python_calc.py
# ===========================
from typing import Dict, Any, Set
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation

class MyPythonDecayCalc(IDecayCalculation):
    """
    Exemple trivial de calcul. 
    On suppose que la largeur partielle dépend d'un param "alpha_em" 
    et de la masse mother. Purement fictif !
    """

    def calculate(self, 
                  mother: int, 
                  daughters: Set[int], 
                  parameters: Dict[str, float]) -> float:
        alpha_em = parameters.get("alpha_em", 1/137.0)

        partial_width = alpha_em * float(mother) / 1e3

        return partial_width
