import importlib.util
import os
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.BranchingRatio.ports.ICalculatorLoader import ICalculatorLoader
import inspect

class BRCalculatorLoader(ICalculatorLoader):
    @staticmethod
    def load_calculator(script_path: str) -> IDecayCalculation:
        """Dynamic loading of BR class calculator from external script.

        Args:
            script_path (str): Path to the python script with the class implementation.

        Returns:
            BranchingRatioCalculator: Instance of the found class.
        """
        module_name = os.path.splitext(os.path.basename(script_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, IDecayCalculation) and obj is not IDecayCalculation:
                return obj()

        raise ValueError(f"No IDecayCalculation subclass found in {script_path}")
