"""Dynamic loader for trusted Python branching-ratio calculators."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.BranchingRatio.ports.ICalculatorLoader import ICalculatorLoader


class BRCalculatorLoader(ICalculatorLoader):
    """Instantiate one concrete decay calculator from a trusted Python script."""

    @staticmethod
    def load_calculator(script_path: str) -> IDecayCalculation:
        """Load the only concrete :class:`IDecayCalculation` in ``script_path``.

        Python calculator files execute during import and must therefore come from
        a trusted source.
        """
        path = Path(script_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)

        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create an import specification for {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        calculators = [
            obj
            for _, obj in inspect.getmembers(module, inspect.isclass)
            if issubclass(obj, IDecayCalculation)
            and obj is not IDecayCalculation
            and obj.__module__ == module.__name__
        ]
        if not calculators:
            raise ValueError(f"No IDecayCalculation subclass found in {path}")
        if len(calculators) > 1:
            names = ", ".join(calculator.__name__ for calculator in calculators)
            raise ValueError(f"Multiple IDecayCalculation subclasses found in {path}: {names}")
        return calculators[0]()
