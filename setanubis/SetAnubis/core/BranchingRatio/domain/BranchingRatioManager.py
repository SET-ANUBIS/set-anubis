"""Management of partial widths, branching ratios, and particle lifetimes."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from SetAnubis.core.BranchingRatio.adapters.output.ConstantCalculationAdapter import (
    ConstantCalculationAdapter,
)
from SetAnubis.core.BranchingRatio.adapters.output.FileInterpolationCalculationAdapter import (
    FileInterpolationCalculationAdapter,
)
from SetAnubis.core.BranchingRatio.adapters.output.MadGraphCalculationAdapter import (
    MadGraphCalculationAdapter,
)
from SetAnubis.core.BranchingRatio.adapters.output.MartyCalculationAdapter import (
    MartyCalculationAdapter,
)
from SetAnubis.core.BranchingRatio.adapters.output.PythonCalculationAdapter import (
    PythonCalculationAdapter,
)
from SetAnubis.core.BranchingRatio.adapters.output.UFOCalculationAdapter import (
    UFOCalculationAdapter,
)
from SetAnubis.core.BranchingRatio.domain.CalculationStrategy import (
    CalculationDecayStrategy,
)
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.BranchingRatio.domain.IDecayChecker import IDecayChecker
from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface


class Unit(Enum):
    """Supported lifetime units."""

    MM = "MM"
    S = "S"
    INVGEV = "INVGEV"


GEV_INV_TO_S = 6.582119569e-25
S_TO_GEV_INV = 1.0 / GEV_INV_TO_S
GEV_INV_TO_MM = 1.0 / 5.0677307e12
MM_TO_GEV_INV = 1.0 / GEV_INV_TO_MM


def convert_lifetime(value: float, from_unit: Unit, to_unit: Unit) -> float:
    """Convert a lifetime between seconds, millimetres, and inverse GeV."""
    if from_unit == to_unit:
        return float(value)

    if from_unit == Unit.S:
        value_in_gev = float(value) * S_TO_GEV_INV
    elif from_unit == Unit.MM:
        value_in_gev = float(value) * MM_TO_GEV_INV
    elif from_unit == Unit.INVGEV:
        value_in_gev = float(value)
    else:  # pragma: no cover - Enum typing prevents this in normal use
        raise ValueError(f"Unknown lifetime unit: {from_unit}")

    if to_unit == Unit.S:
        return value_in_gev * GEV_INV_TO_S
    if to_unit == Unit.MM:
        return value_in_gev * GEV_INV_TO_MM
    if to_unit == Unit.INVGEV:
        return value_in_gev
    raise ValueError(f"Unknown lifetime unit: {to_unit}")


class BranchingRatioManager:
    """Register decay providers and derive widths, branching ratios, and lifetimes."""

    def __init__(self, decay_checker: IDecayChecker, model: SetAnubisInterface) -> None:
        """Create a manager backed by a decay checker and model interface."""
        self._decays: Dict[Tuple[int, Tuple[int, ...]], IDecayCalculation] = {}
        self._decay_checker = decay_checker
        self.nsa = model
        self._lifetimes: Dict[int, float] = {}

    def add_decay(
        self,
        mother: int,
        daughters: MultiSet[int],
        strategy: CalculationDecayStrategy,
        config: Dict[str, Any],
    ) -> None:
        """Register one decay channel and its calculation strategy."""
        self._decay_checker.check_decay_validity(mother, daughters, self.nsa)
        self._decays[self._key(mother, daughters)] = self._create_strategy(
            strategy, config
        )

    def add_decays(
        self,
        decay_list: List[Dict[str, Any]],
        strategy: CalculationDecayStrategy,
        common_config: Dict[str, Any],
    ) -> None:
        """Register several channels that share one calculation strategy."""
        calculation = self._create_strategy(strategy, common_config)
        for decay_info in decay_list:
            mother = int(decay_info["mother"])
            daughters = decay_info["daughters"]
            self._decay_checker.check_decay_validity(mother, daughters, self.nsa)
            self._decays[self._key(mother, daughters)] = calculation

    def add_constant_decay(
        self,
        mother: int,
        daughters: MultiSet[int],
        value: float,
        *,
        is_br: bool = False,
    ) -> None:
        """Register a manually supplied width or branching ratio."""
        self.add_decay(
            mother,
            daughters,
            CalculationDecayStrategy.CONSTANT,
            {"value": value, "BR": is_br},
        )

    def add_special_lifetime(self, particle: int, value: float, unit: Unit) -> None:
        """Override the width-derived lifetime for one particle."""
        if value <= 0.0:
            raise ValueError("A lifetime override must be strictly positive")
        self._lifetimes[int(particle)] = convert_lifetime(
            value, from_unit=unit, to_unit=Unit.INVGEV
        )

    def calculate_lifetime(self, particle: int, unit: Unit) -> float:
        """Return a lifetime override or compute ``1 / total_width``."""
        if particle in self._lifetimes:
            value_in_gev = self._lifetimes[particle]
        else:
            total_width = self.calculate_total_decay(particle)
            if total_width <= 0.0:
                raise ValueError(
                    f"No positive total decay width is available for particle {particle}"
                )
            value_in_gev = 1.0 / total_width
        return convert_lifetime(value_in_gev, Unit.INVGEV, unit)

    def calculate_decay(self, mother: int, daughters: MultiSet[int]) -> float:
        """Calculate the registered observable for one kinematically allowed channel."""
        key = self._key(mother, daughters)
        if key not in self._decays:
            raise ValueError(
                f"No decay registered for mother={mother}, daughters={list(daughters)}"
            )

        mother_mass = float(self.nsa.get_particle_mass(abs(mother)).real)
        daughter_mass = sum(
            float(self.nsa.get_particle_mass(abs(daughter)).real)
            for daughter in daughters
        )
        if mother_mass <= daughter_mass:
            return 0.0

        parameters = self._numeric_parameters(self.nsa.get_all_parameters())
        return float(self._decays[key].calculate(mother, daughters, parameters))

    def calculate_total_decay(self, mother: int) -> float:
        """Sum registered partial widths, excluding dimensionless BR providers."""
        total_width = 0.0
        for key, calculation in self._decays.items():
            if key[0] == mother and not calculation.is_br():
                total_width += self.calculate_decay(key[0], key[1])
        return total_width

    def calculate_branching_ratios_for_mother(
        self, mother: int
    ) -> List[Dict[str, Any]]:
        """Return partial values and branching ratios for every registered channel."""
        relevant_keys = [key for key in self._decays if key[0] == mother]
        if not relevant_keys:
            raise ValueError(f"No decays registered for mother={mother}")

        total_width = self.calculate_total_decay(mother)
        results: list[dict[str, Any]] = []
        for key in relevant_keys:
            partial_value = self.calculate_decay(key[0], key[1])
            calculation = self._decays[key]
            if calculation.is_br():
                branching_ratio = partial_value
            elif total_width > 0.0:
                branching_ratio = partial_value / total_width
            else:
                branching_ratio = 0.0
            results.append(
                {
                    "mother": key[0],
                    "daughters": list(key[1]),
                    "partial_width": partial_value,
                    "branching_ratio": branching_ratio,
                }
            )
        return results

    def calculate_branching_ratio_for_mother(
        self,
        mother: int,
        daughters: MultiSet[int],
    ) -> float:
        """Return the branching ratio for one registered channel."""
        key = self._key(mother, daughters)
        if key not in self._decays:
            raise ValueError(
                f"No decay registered for mother={mother}, daughters={list(daughters)}"
            )
        partial_value = self.calculate_decay(mother, daughters)
        if self._decays[key].is_br():
            return partial_value
        total_width = self.calculate_total_decay(mother)
        return partial_value / total_width if total_width > 0.0 else 0.0

    def get_all_decays(
        self,
        mother: Optional[int] = None,
    ) -> Dict[Tuple[int, Tuple[int, ...]], IDecayCalculation] | List[Tuple[int, ...]]:
        """Return all registered calculations or daughter tuples for one mother."""
        if mother is None:
            return dict(self._decays)
        return [daughters for registered_mother, daughters in self._decays if registered_mother == mother]

    @staticmethod
    def _key(mother: int, daughters: MultiSet[int]) -> Tuple[int, Tuple[int, ...]]:
        """Build the canonical dictionary key for a decay channel."""
        return int(mother), tuple(sorted(int(value) for value in daughters))

    @staticmethod
    def _numeric_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten model metadata into values accepted by calculation adapters.

        The model interface stores evaluated parameters as dictionaries containing
        a ``value`` field plus optional Les Houches metadata.  Calculation adapters
        operate on numerical values, so this method removes that wrapper while
        preserving genuinely complex values.
        """
        numeric: Dict[str, Any] = {}
        for name, entry in parameters.items():
            value = entry.get("value") if isinstance(entry, dict) and "value" in entry else entry
            if isinstance(value, complex) and abs(value.imag) <= 1e-15:
                value = value.real
            numeric[name] = value
        return numeric

    def _create_strategy(
        self,
        strategy_type: CalculationDecayStrategy,
        config: Dict[str, Any],
    ) -> IDecayCalculation:
        """Create a calculation adapter from a strategy and configuration mapping."""
        is_br = bool(config.get("BR", False))
        if strategy_type == CalculationDecayStrategy.CONSTANT:
            return ConstantCalculationAdapter(config["value"], is_br)
        if strategy_type == CalculationDecayStrategy.UFO:
            return UFOCalculationAdapter(config["ufo_path"], is_br)
        if strategy_type == CalculationDecayStrategy.PYTHON:
            return PythonCalculationAdapter(config["script_path"], is_br)
        if strategy_type == CalculationDecayStrategy.FILE_INTERPOLATION:
            return FileInterpolationCalculationAdapter(
                config["file_path"],
                config["varying_params"],
                is_br,
                config.get("format_type", "csv"),
            )
        if strategy_type == CalculationDecayStrategy.MADGRAPH:
            return MadGraphCalculationAdapter(config.get("calculator"), is_br)
        if strategy_type == CalculationDecayStrategy.MARTY:
            return MartyCalculationAdapter(
                self.nsa,
                config.get("model_name", "SM"),
                is_br,
                mapping_dir=config.get("mapping_dir"),
                model_path=config.get("model_path"),
                marty_path=config.get("marty_path"),
                workspace_dir=config.get("workspace_dir"),
                template_dir=config.get("template_dir"),
                mediator_fermion_orders=config.get("mediator_fermion_orders"),
            )
        raise ValueError(f"Unknown decay calculation strategy: {strategy_type}")
