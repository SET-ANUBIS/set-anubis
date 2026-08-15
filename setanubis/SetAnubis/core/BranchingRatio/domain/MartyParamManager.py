"""Extract MARTY parameters from generated headers and serialize input tables."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import numpy as np

from SetAnubis.core.BranchingRatio.domain.MartyUtil import (
    load_particle_mappings,
    load_ufo_mappings,
)
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface


class ParameterType(Enum):
    """C++ parameter representations emitted by MARTY."""

    REAL = "real_t"
    COMPLEX = "complex_t"


@dataclass
class Parameter:
    """One generated MARTY parameter and its corresponding UFO value."""

    name: str
    type: ParameterType
    ufo_name: str
    value: Optional[complex] = None


class ParamManager:
    """Map generated MARTY parameters and particles back to a UFO model."""

    def __init__(
        self,
        header_path: Path,
        nsa: SetAnubisInterface,
        mapping_dir: Path | str | None = None,
    ) -> None:
        """Parse ``header_path`` and evaluate every supported model parameter."""
        self.nsa = nsa
        self.header_path = Path(header_path)
        self.mapping_dir = mapping_dir
        self.cpp_param_names: Dict[str, ParameterType] = self._parse_cpp_header()
        self.parameters: List[Parameter] = []
        self.excluded: Set[str] = {"s_12", "s_13", "s_14", "s_23", "s_34", "s_24"}
        self.special: Set[str] = {"sw", "reg_prop", "Finite"}
        if self.mapping_dir is None:
            self.ufo_map = load_ufo_mappings()
            self.ufo_part_map = load_particle_mappings()
        else:
            self.ufo_map = load_ufo_mappings(mapping_dir=self.mapping_dir)
            self.ufo_part_map = load_particle_mappings(mapping_dir=self.mapping_dir)
        self._initialize_parameters()

    def _parse_cpp_header(self) -> Dict[str, ParameterType]:
        """Extract real and complex initializer names from a generated header."""
        content = self.header_path.read_text(encoding="utf-8")
        patterns = {
            ParameterType.REAL: r"csl::InitSanitizer<real_t>\s+(\w+)\s*{",
            ParameterType.COMPLEX: r"csl::InitSanitizer<complex_t>\s+(\w+)\s*{",
        }
        parameters: Dict[str, ParameterType] = {}
        for parameter_type, pattern in patterns.items():
            parameters.update(
                {name: parameter_type for name in re.findall(pattern, content)}
            )
        return parameters

    def _get_ufo_name(self, parameter_name: str) -> str:
        """Return the UFO name mapped from a generated MARTY parameter."""
        return self.ufo_map.get(parameter_name, parameter_name)

    def _get_ufo_part_name(self, particle_name: str) -> str:
        """Return the UFO particle name mapped from a MARTY particle name."""
        return self.ufo_part_map.get(particle_name, particle_name)

    def _initialize_parameters(self) -> None:
        """Create parameter records with names, types, mappings, and values."""
        for name, parameter_type in self.cpp_param_names.items():
            if name in self.excluded:
                continue
            ufo_name = self._get_ufo_name(name)
            self.parameters.append(
                Parameter(
                    name=name,
                    type=parameter_type,
                    ufo_name=ufo_name,
                    value=self.get_value(ufo_name),
                )
            )

    def get_value(self, ufo_name: str) -> Optional[complex]:
        """Return a generated constant or query the model parameter service."""
        special = self._special(ufo_name)
        if special is not None:
            return complex(special)
        return complex(self.nsa.get_parameter_value(ufo_name))

    def _special(self, ufo_name: str) -> Optional[float]:
        """Resolve constants that are not direct UFO parameters."""
        if ufo_name == "reg_prop":
            return 0.00001
        if ufo_name == "theta_W":
            return float(np.arcsin(self.nsa.get_parameter_value("sw").real))
        if ufo_name == "Finite":
            return 1.0
        return None

    def get_parameters(self) -> List[Parameter]:
        """Return generated parameters in header declaration order."""
        return list(self.parameters)

    def as_dict(self) -> Dict[str, dict]:
        """Export parameters as serializable dictionaries for inspection."""
        output: Dict[str, dict] = {}
        for parameter in self.parameters:
            if parameter.type == ParameterType.COMPLEX and parameter.value is not None:
                output[parameter.name] = {
                    "type": parameter.type.value,
                    "ufo_name": parameter.ufo_name,
                    "value_real": float(parameter.value.real),
                    "value_img": float(parameter.value.imag),
                }
            else:
                value = None if parameter.value is None else float(parameter.value.real)
                output[parameter.name] = {
                    "type": parameter.type.value,
                    "ufo_name": parameter.ufo_name,
                    "value": value,
                }
        return output

    def create_csv(self) -> str:
        """Serialize parameter values as the two-column MARTY input format."""
        lines: List[str] = []
        for parameter in self.get_parameters():
            if parameter.value is None:
                continue
            if parameter.type == ParameterType.COMPLEX:
                lines.append(f"{parameter.name}_rel,{float(parameter.value.real)}")
                lines.append(f"{parameter.name}_img,{float(parameter.value.imag)}")
            else:
                lines.append(f"{parameter.name},{float(parameter.value.real)}")
        return "\n".join(lines) + ("\n" if lines else "")

    def create_particle_csv(
        self,
        mothers: Iterable[int],
        daughters: Iterable[int],
    ) -> str:
        """Serialize incoming and outgoing particle names and masses."""
        lines: List[str] = []
        for particle in mothers:
            lines.append(
                f"{self.nsa.get_particle_info(particle)['name']}_in,"
                f"{self.nsa.get_particle_mass(particle)}"
            )
        for particle in daughters:
            lines.append(
                f"{self.nsa.get_particle_info(particle)['name']}_out,"
                f"{self.nsa.get_particle_mass(particle)}"
            )
        return "\n".join(lines) + ("\n" if lines else "")
