from typing import Dict, Any, Set, List
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.BranchingRatio.adapters.output.CSVInterpolationSubStrategy import CSVInterpolationSubStrategy

class FileInterpolationCalculationAdapter(IDecayCalculation):
    """
    Strategy pour la calculation "FILE_INTERPOLATION".
    On délègue à un "sub_strategy" (CSV, JSON, etc.).
    """

    def __init__(self, file_path: str, varying_params: List[str], is_br = False, format_type: str = "csv"):
        self.file_path = file_path
        self.varying_params = varying_params
        self.format_type = format_type
        self._is_br = is_br
        self._sub_strategy = self._choose_sub_strategy(format_type)
        self._sub_strategy.load_file(file_path, varying_params)

    def _choose_sub_strategy(self, format_type: str):
        if format_type.lower() == "csv":
            return CSVInterpolationSubStrategy()
        # elif format_type.lower() == "json":
        #     return JSONInterpolationSubStrategy()
        # ...
        else:
            raise ValueError(f"Unsupported format '{format_type}' for File Interpolation")

    def calculate(self, 
                  mother: int, 
                  daughters: Set[int], 
                  parameters: Dict[str, float]) -> float:
        return self._sub_strategy.interpolate(mother, daughters, parameters)
