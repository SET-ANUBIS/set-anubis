"""Adapter for decay observables tabulated in supported file formats."""

from __future__ import annotations

from typing import Dict, List

from SetAnubis.core.BranchingRatio.adapters.output.CSVInterpolationSubStrategy import (
    CSVInterpolationSubStrategy,
)
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.Common.MultiSet import MultiSet


class FileInterpolationCalculationAdapter(IDecayCalculation):
    """Interpolate a partial width or branching ratio from a data file."""

    def __init__(
        self,
        file_path: str,
        varying_params: List[str],
        is_br: bool = False,
        format_type: str = "csv",
    ) -> None:
        """Load a table and configure the observable type."""
        self.file_path = file_path
        self.varying_params = list(varying_params)
        self.format_type = format_type
        self._is_br = bool(is_br)
        self._sub_strategy = self._choose_sub_strategy(format_type)
        self._sub_strategy.load_file(file_path, self.varying_params, is_br=is_br)

    @staticmethod
    def _choose_sub_strategy(format_type: str) -> CSVInterpolationSubStrategy:
        """Return the parser/interpolator associated with ``format_type``."""
        if format_type.lower() == "csv":
            return CSVInterpolationSubStrategy()
        raise ValueError(f"Unsupported file-interpolation format: {format_type!r}")

    def calculate(
        self,
        mother: int,
        daughters: MultiSet[int],
        parameters: Dict[str, float],
    ) -> float:
        """Interpolate the requested decay channel at ``parameters``."""
        return float(self._sub_strategy.interpolate(mother, daughters, parameters))
