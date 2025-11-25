from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
import pandas as pd
from typing import Optional, Dict, List, Set
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.domain.MartyUtil import load_ufo_mappings, load_particle_mappings
import numpy as np

class ParameterType(Enum):
    REAL = "real_t"
    COMPLEX = "complex_t"


@dataclass
class Parameter:
    name: str
    type: ParameterType
    ufo_name: str
    value: Optional[complex] = None


class ParamManager:
    def __init__(self, header_path: Path, nsa : SetAnubisInterface):
        self.nsa : SetAnubisInterface = nsa 
        self.header_path : Path= header_path
        self.cpp_param_names: Dict[str, ParameterType] = self._parse_cpp_header()
        self.parameters: List[Parameter] = []
        self.excluded : Set[str] = {"s_12", "s_13", "s_14", "s_23", "s_34", "s_24"}
        self.special : Set[str] = {"sw", "reg_prop", "Finite"} #TODO : deal with this
        self.ufo_map = load_ufo_mappings()
        self.ufo_part_map = load_particle_mappings()
        self._initialize_parameters()

    def _parse_cpp_header(self) -> Dict[str, ParameterType]:
        """
        Parse the given C++ header file and extract InitSanitizer parameters.
        """
        real_pattern = r'csl::InitSanitizer<real_t>\s+(\w+)\s*{'
        complex_pattern = r'csl::InitSanitizer<complex_t>\s+(\w+)\s*{'

        real_params = {}
        complex_params = {}

        content = self.header_path.read_text()

        for match in re.findall(real_pattern, content):
            real_params[match] = ParameterType.REAL
        for match in re.findall(complex_pattern, content):
            complex_params[match] = ParameterType.COMPLEX

        return {**real_params, **complex_params}

    

    def _get_ufo_name(self, param_name: str) -> str:
        return self.ufo_map.get(param_name, param_name)

    def _get_ufo_part_name(self, part_name: str) -> str:
        return self.ufo_part_map.get(part_name, part_name)
    
    def _initialize_parameters(self):
        """
        Initialize the list of Parameter objects with names, types, UFO names and values.
        """
        for name, param_type in self.cpp_param_names.items():
            if name in self.excluded:
                continue
            ufo_name = self._get_ufo_name(name)
            value = self.get_value(ufo_name)
            param = Parameter(name=name, type=param_type, ufo_name=ufo_name, value=value)
            self.parameters.append(param)

    def get_value(self, ufo_name: str) -> Optional[float]:
        """
        Placeholder for the actual value-fetching mechanism.
        Replace this method with your actual logic.
        """
        special = self._special(ufo_name)
        if special:
            return complex(special, 0)
        
        return self.nsa.get_parameter_value(ufo_name)

    def _special(self,ufo_name):
        if ufo_name == "reg_prop":
            return 0.00001
        elif ufo_name == "theta_W":
            return np.asin(self.nsa.get_parameter_value("sw").real)
        elif ufo_name == "Finite":
            return 1
        return None
    def get_parameters(self) -> List[Parameter]:
        return self.parameters

    def as_dict(self) -> Dict[str, dict]:
        """
        Export parameters as dictionary for easier use/debugging.
        Pour les complexes, expose value_real / value_img.
        """
        out: Dict[str, dict] = {}
        for p in self.parameters:
            if p.type == ParameterType.COMPLEX and p.value is not None:
                out[p.name] = {
                    "type": p.type.value,
                    "ufo_name": p.ufo_name,
                    "value_real": float(p.value.real),
                    "value_img": float(p.value.imag),
                }
            else:
                val = None if p.value is None else float(p.value.real)
                out[p.name] = {
                    "type": p.type.value,
                    "ufo_name": p.ufo_name,
                    "value": val,
                }
        return out

    def create_csv(self) -> str:
        """
        Construit le CSV. Les paramètres complexes donnent deux lignes:
        name_rel,<Re(value)>
        name_img,<Im(value)>
        """
        lines: List[str] = []
        for p in self.get_parameters():
            if p.value is None:
                continue
            if p.type == ParameterType.COMPLEX:
                lines.append(f"{p.name}_rel,{float(p.value.real)}")
                lines.append(f"{p.name}_img,{float(p.value.imag)}")
            else:
                lines.append(f"{p.name},{float(p.value.real)}")
        return "\n".join(lines) + ("\n" if lines else "")
    
    
    def create_particle_csv(self, mothers, daugthers) -> str:
        lines : List[str] = []
        
        for p in mothers:
            lines.append(f"{self.nsa.get_particle_info(p)['name']}_in,{self.nsa.get_particle_mass(p)}")
            
        for p in daugthers:
            lines.append(f"{self.nsa.get_particle_info(p)['name']}_out,{self.nsa.get_particle_mass(p)}")
            
        return "\n".join(lines) + ("\n" if lines else "")
    
if __name__ == "__main__":
    header_file = Path("Assets/MARTY/MartyTemp/libs/decay_widths_23_s_2_2/include/params.h")  # ← à adapter
    nsa = SetAnubisInterface("Assets/UFO/UFO_HNL")
    manager = ParamManager(header_path=header_file, nsa=nsa)
    # for param in manager.get_parameters():
    #     print(f"{param.name} ({param.type.name}): {param.value} (UFO: {param.ufo_name})")
        
    print(manager.create_csv())