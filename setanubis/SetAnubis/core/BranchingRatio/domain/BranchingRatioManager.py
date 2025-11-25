from typing import Dict, Any, List, Set, Tuple
from SetAnubis.core.Common.MultiSet import MultiSet
# from SetAnubis.core.BranchingRatio.ports.IBranchingRatioManager import IBranchingRatioManager
from SetAnubis.core.BranchingRatio.domain.CalculationStrategy import CalculationDecayStrategy
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.BranchingRatio.domain.IDecayChecker import IDecayChecker
from SetAnubis.core.BranchingRatio.adapters.output.UFOCalculationAdapter import UFOCalculationAdapter
from SetAnubis.core.BranchingRatio.adapters.output.PythonCalculationAdapter import PythonCalculationAdapter
from SetAnubis.core.BranchingRatio.adapters.output.FileInterpolationCalculationAdapter import FileInterpolationCalculationAdapter
from SetAnubis.core.BranchingRatio.adapters.output.MadGraphCalculationAdapter import MadGraphCalculationAdapter
from SetAnubis.core.BranchingRatio.adapters.output.MartyCalculationAdapter import MartyCalculationAdapter
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from enum import Enum
import numpy as np

class Unit(Enum):
    MM = "MM"
    S = "S"
    INVGEV = "INVGEV"
    
#TODO : set elswhere.
GEV_INV_TO_S = 6.582119569e-25
S_TO_GEV_INV = 1 / GEV_INV_TO_S

GEV_INV_TO_MM = 1 / 5.0677307e+12
MM_TO_GEV_INV = 1 / GEV_INV_TO_MM

def convert_lifetime(value: float, from_unit: Unit, to_unit: Unit) -> float:
    if from_unit == to_unit:
        return value

    if from_unit == Unit.S:
        value_in_gev = value * S_TO_GEV_INV
    elif from_unit == Unit.MM:
        value_in_gev = value * MM_TO_GEV_INV
    elif from_unit == Unit.INVGEV:
        value_in_gev = value
    else:
        raise ValueError(f"Unknown from_unit: {from_unit}")

    if to_unit == Unit.S:
        return value_in_gev * GEV_INV_TO_S
    elif to_unit == Unit.MM:
        return value_in_gev * GEV_INV_TO_MM
    elif to_unit == Unit.INVGEV:
        return value_in_gev
    else:
        raise ValueError(f"Unknown to_unit: {to_unit}")

class BranchingRatioManager:
    """Main manager class for handling particle decays with various calculation strategies.

    Responsible for registering decay processes, verifying their validity, and calculating
    branching ratios and decay widths.

    Attributes:
        _decays (Dict[Tuple[int, Tuple[int]], IDecayCalculation]):
            Dictionary mapping decay processes to their calculation strategies.
        _decay_checker (IDecayChecker):
            Checker to verify the validity of decay processes.
        nsa (NeoSetAnubisInterface):
            Interface for retrieving particle information and parameters.
        params (Dict[str, Any]):
            Parameters retrieved from SetAnubisInterface.
    """

    def __init__(self, decay_checker: IDecayChecker, nsa : SetAnubisInterface):
        """Initializes BranchingRatioManager with decay checker and parameter interface.

        Args:
            decay_checker (IDecayChecker): Decay validity checker.
            nsa (NeoSetAnubisInterface): Interface for accessing parameters and particle information.
        """
        self._decays: Dict[(int, tuple), IDecayCalculation] = {}
        self._decay_checker = decay_checker
        self.nsa = nsa
        self._lifetimes : Dict = {}

    def add_decay(self, 
                  mother: int, 
                  daughters: MultiSet[int], 
                  strategy: CalculationDecayStrategy, 
                  config: Dict[str, Any]) -> None:
        """Registers a single decay process.

        Args:
            mother (int): Mother particle PDG code.
            daughters (MultiSet[int]): Daughter particle PDG codes.
            strategy (CalculationDecayStrategy): Strategy for calculating decay.
            config (Dict[str, Any]): Configuration parameters for the calculation strategy.
        """
        self._decay_checker.check_decay_validity(mother, daughters, self.nsa)

        calc_strategy = self._create_strategy(strategy, config)

        key = (mother, tuple(sorted(daughters)))
        self._decays[key] = calc_strategy
        
        
    def add_decays(self,
                decay_list: List[Dict[str, Any]],
                strategy: CalculationDecayStrategy,
                common_config: Dict[str, Any]) -> None:
        """Registers multiple decay processes using the same calculation strategy and configuration.

        Args:
            decay_list (List[Dict[str, Any]]): List of decay processes with mother and daughters.
            strategy (CalculationDecayStrategy): Calculation strategy.
            common_config (Dict[str, Any]): Common configuration parameters.
        """

        calc_strategy = self._create_strategy(strategy, common_config)

        for decay_info in decay_list:
            mother = decay_info["mother"]
            daughters = decay_info["daughters"]
            
            self._decay_checker.check_decay_validity(mother, daughters, self.nsa)
            
            key = (mother, tuple(sorted(daughters)))
            self._decays[key] = calc_strategy
        
    def add_special_lifetime(self, particle : int, value : float, unit : Unit):
        """Set a particular lifetime for a particle, will be used instead of the 1/Total_Width if set.

        Args:
            particle (int): Particle PDG code.
            value (float): The value of the wanted lifetime.
            unit (Unit): The unit in which the lifetime is given.
        """
        if value == 0:
            raise ValueError("Invalid lifetime, please choose non zero lifetime.")
        
        value_in_gev = convert_lifetime(value, from_unit=unit, to_unit=Unit.INVGEV)
        self._lifetimes[particle] = value_in_gev
        
        
    def calculate_lifetime(self, particle : int, unit : Unit):
        """Calculate the lifetime for a particle and use the value in _lifetimes instead of the 1/Total_Width if set.

        Args:
            particle (int): Particle PDG code.
            unit (Unit): The unit in which the lifetime is given.
            
            Returns:
            float: The calculated lifetime in the unit precised by the user.
        """
        if particle in self._lifetimes:
            value_in_gev = self._lifetimes[particle]
        else:
            total_width = self.calculate_total_decay(particle)
            if total_width == 0:
                raise ValueError(f"Total decay width is zero for particle {particle}, cannot compute lifetime.")
            value_in_gev = 1 / total_width 
        
        return convert_lifetime(value_in_gev, from_unit=Unit.INVGEV, to_unit=unit)
    
    def calculate_decay(self, mother: int, daughters: MultiSet[int]) -> float:
        """Calculates the decay width for a specific decay process.

        Args:
            mother (int): Mother particle PDG code.
            daughters (MultiSet[int]): Daughter particle PDG codes.

        Returns:
            float: Calculated decay width.
        """
        key = (mother, tuple(sorted(daughters)))
        if key not in self._decays:
            raise ValueError(f"No decay registered for mother={mother}, daughters={daughters}")
        
        if mother > 0:
            mother_mass = self.nsa.get_particle_mass(mother).real
        #   mother_mass = float(self.nsa.get_particle_info(mother).get("mass", 0).real)
        else:
            mother_mass = self.nsa.get_particle_mass(-mother).real
        #   mother_mass = float(self.nsa.get_particle_info(-mother).get("mass", 0).real)
        # self._particles_info[mother].get("mass", 0)
        # mother_mass = self._particles_info[mother]["mass"]
        total_daughters_mass = sum(float(self.nsa.get_particle_mass(d).real) if d > 0 else float(self.nsa.get_particle_mass(-d).real) for d in daughters)
        # total_daughters_mass = sum(self._particles_info[d]["mass"] for d in daughters)
        if mother_mass <= total_daughters_mass:
            return 0.0
            raise ValueError(f"Cannot decay: mother mass ({mother_mass}) "
                             f"<= sum of daughters mass ({total_daughters_mass}).")

        calc_strategy = self._decays[key]

   
        # all_params = {}  #TODO
        all_params = self.nsa.get_all_parameters()
        result = calc_strategy.calculate(mother, daughters, all_params)
        return result

    def calculate_total_decay(self, mother: int) -> float:
        """
        
        Args:
            mother (int): Mother particle PDG code.
            
        Compute the total decay width of a mother particle,
        by summing over all partial widths for registered mother -> daughters decays
        in self._decays.
        
        Returns:
            float: Calculated total decay width.
        """
        relevant_decays = [
            (k, v) for k, v in self._decays.items() if k[0] == mother
        ]
        total_width = 0.0
        for (m, daughters_tuple), _calc_strategy in relevant_decays:
            partial = self.calculate_decay(m, daughters_tuple)
            total_width += partial
        return total_width
    
    def calculate_branching_ratios_for_mother(self, mother: int) -> List[Dict[str, Any]]:
        """
        Retourne la liste des canaux mother->daughters,
        avec leur largeur partielle et leur BR = partial/total.
        """
        relevant_keys = [
            key for key in self._decays.keys() if key[0] == mother
        ]
        if not relevant_keys:
            raise ValueError(f"No decays registered for mother={mother}.")

        total_width = self.calculate_total_decay(mother)

        results = []
        for (m, daughters_tuple) in relevant_keys:
            partial_width = self.calculate_decay(m, daughters_tuple)
            if total_width > 0.0:
                key = (m, tuple(sorted(daughters_tuple)))
                if self._decays[key].is_br():
                    br = partial_width
                else:
                    br = partial_width / total_width
            else:
                br = 0.0
            results.append({
                "mother": m,
                "daughters": list(daughters_tuple),
                "partial_width": partial_width,
                "branching_ratio": br
            })
        return results
    
    def calculate_branching_ratio_for_mother(self, mother: int, daugthers : MultiSet[int]) -> List[Dict[str, Any]]:
        """
        Retourne la liste des canaux mother->daughters,
        avec leur largeur partielle et leur BR = partial/total.
        """
        relevant_keys = [
            key for key in self._decays.keys() if key[0] == mother
        ]
        if not relevant_keys:
            raise ValueError(f"No decays registered for mother={mother}.")

        total_width = self.calculate_total_decay(mother)
        partial_width = self.calculate_decay(mother, daugthers)
        if total_width > 0.0:
            key = (mother, tuple(sorted(daugthers)))
            if self._decays[key].is_br():
                br = partial_width
            else:
                br = partial_width / total_width
        else:
            br = 0.0
        return br
    
    def get_all_decays(self, mother : int = None):
        if mother is None:
            return self._decays
        return [y for x,y in self._decays.keys() if x == mother]
    
    def _create_strategy(self, strategy_type: CalculationDecayStrategy, config: Dict[str, Any]) -> IDecayCalculation:
        """Creates a calculation strategy based on the specified type and configuration.

        Args:
            strategy_type (CalculationDecayStrategy): Type of calculation strategy.
            config (Dict[str, Any]): Configuration parameters for the strategy.

        Returns:
            IDecayCalculation: Instance of the selected calculation strategy.
        """
        
        is_br = config.get("BR", False)
        
        if strategy_type == CalculationDecayStrategy.UFO:
            return UFOCalculationAdapter(config["ufo_path"], is_br)
        elif strategy_type == CalculationDecayStrategy.PYTHON:
            return PythonCalculationAdapter(config["script_path"], is_br)
        elif strategy_type == CalculationDecayStrategy.FILE_INTERPOLATION:
            return FileInterpolationCalculationAdapter(config["file_path"], config["varying_params"], is_br)
        elif strategy_type == CalculationDecayStrategy.MADGRAPH:
            return MadGraphCalculationAdapter()
        elif strategy_type == CalculationDecayStrategy.MARTY:
            return MartyCalculationAdapter()
        else:
            raise ValueError(f"Unknown strategy {strategy_type}")

    
        
            