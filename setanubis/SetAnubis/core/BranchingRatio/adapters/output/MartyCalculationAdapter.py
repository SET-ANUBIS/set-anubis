"""MARTY-backed adapter for symbolic and numerical decay calculations."""

from __future__ import annotations

from typing import Dict

from SetAnubis.core.BranchingRatio.adapters.output.MartyFileCopyBuilder import (
    MartyFileCopyBuilder,
)
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.BranchingRatio.domain.MartyManager import MartyManager
from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface


class MartyCalculationAdapter(IDecayCalculation):
    """Generate and execute a MARTY decay-width calculation on demand."""

    def __init__(
        self,
        model: SetAnubisInterface,
        model_name: str = "SM",
        is_br: bool = False,
    ) -> None:
        """Configure MARTY with a SetAnubis model and MARTY model name."""
        self.model = model
        self.manager = MartyManager(model_name)
        self.copy_builder = MartyFileCopyBuilder()
        self._is_br = bool(is_br)

    def calculate(
        self,
        mother: int,
        daughters: MultiSet[int],
        parameters: Dict[str, float],
    ) -> float:
        """Build and run the analytic and numerical MARTY stages."""
        del parameters
        return float(
            self.manager.calculate_process(
                [mother],
                list(daughters),
                self.model,
                self.copy_builder,
            )
        )
