import csv
from SetAnubis.core.BranchingRatio.ports.IFileInterpolationStrategy import IFileInterpolationSubStrategy
from typing import Dict, Any, Set, List


class CSVInterpolationSubStrategy(IFileInterpolationSubStrategy):
    def __init__(self):
        self._data = []
        self._varying_params = []

    def load_file(self, file_path: str, varying_params: List[str], is_br = False):
        self._varying_params = varying_params
        self._is_br = is_br
        with open(file_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._data.append(row)

    def interpolate(self, mother: int, daughters: List[int], param_values: Dict[str, float]) -> float:
        """
        Exemple d'implémentation:
        - On trouve la ligne la plus proche (ou on fait une interpolation multi-D).
        - On récupère la colonne mother:daughters. 
        - On renvoie la valeur correspondante comme "largeur partielle".
                """

        for p in self._varying_params:
            if p not in param_values.keys():
                raise ValueError(f"Parameter {p} not in varying_params. Can't do interpolation.")
        
        best_row = None
        for row in self._data:
            match_all = True

            if match_all:
                best_row = row
                break
        
        if best_row is None:
            raise ValueError("No matching row found in CSV for these parameter values.")
        
        mother_str = str(mother)
        daughters_sorted = list(daughters)
        daughters_str = ";".join(str(d) for d in daughters_sorted)
        col_name = f"{mother_str}:{daughters_str}"

        if col_name not in best_row:
            raise KeyError(f"No column '{col_name}' in CSV row. Available columns: {list(best_row.keys())}")

        partial_width_str = best_row[col_name]
        partial_width = float(partial_width_str)
        return partial_width
