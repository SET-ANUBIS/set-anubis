from SetAnubis.core.BranchingRatio.domain.BranchingRatioManager import BranchingRatioManager, Unit
from SetAnubis.core.BranchingRatio.domain.DecayChecker import DecayChecker
from SetAnubis.core.BranchingRatio.domain.CalculationStrategy import CalculationDecayStrategy
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.Common.MultiSet import MultiSet
from typing import List, Dict, Tuple, Any

class DecayInterface:
    """
    Interface for managing particle decays and branching ratios.

    This class acts as a simplified interface to the `BranchingRatioManager`, 
    facilitating access to decay calculations and branching ratio management 
    using the `NeoSetAnubisInterface` as a data source.

    Args:
        nsa (NeoSetAnubisInterface): Interface providing access to particle data 
            and decay-related information.

    Attributes:
        nsa (NeoSetAnubisInterface): The particle data interface instance.
        br_manager (BranchingRatioManager): Manager handling decay calculations 
            and branching ratio logic.

    Methods:
        get_decay(mother: int, daughter: MultiSet[int]) -> float:
            Returns the decay probability of a mother particle into a specific set of daughters.
        
        set_decay(mother: int, daughters: MultiSet[int], value):
            Adds or updates the decay probability for a mother-daughters configuration.
        
        get_decay_tot(mother: int) -> float:
            Returns the total decay probability of the given mother particle.
        
        get_brs(mother):
            Returns all branching ratios for the specified mother particle.
        
        get_br(mother, daughter):
            Returns the branching ratio for a specific mother-daughters configuration.
        
        add_decays(decays_list: List, strategy: CalculationDecayStrategy, config: Dict):
            Adds a list of decays using a specified calculation strategy and configuration.
        
        get_all_decays(mother: int = None) -> List[Tuple]:
            Retrieves all registered decays, optionally filtered by mother particle.
    """
    def __init__(self, nsa : SetAnubisInterface):
        self.nsa = nsa
        self.br_manager = BranchingRatioManager(DecayChecker(), nsa)
        # self.br_manager.set_particle_info(all_particles)
        
    def get_decay(self, mother : int, daughter : MultiSet[int]) -> float:
        """
        Retrieve the decay probability of a mother particle into a given set of daughter particles.

        Args:
            mother (int): The ID of the mother particle.
            daughter (MultiSet[int]): A multiset representing the daughter particles.

        Returns:
            float: The decay probability for the specified decay channel.
        """
        return self.br_manager.calculate_decay(mother, daughter)
    
    def set_decay(self, mother : int, daughters : MultiSet[int], value):
        """
        Set or update the decay probability for a given decay channel.

        Args:
            mother (int): The ID of the mother particle.
            daughters (MultiSet[int]): A multiset representing the daughter particles.
            value: The decay probability to assign to this decay channel.

        Returns:
            None
        """
        return self.br_manager.add_decay(mother, daughters, value)
    
    def get_decay_tot(self, mother : int) -> float:
        """
        Calculate the total decay probability for a given mother particle.

        Args:
            mother (int): The ID of the mother particle.

        Returns:
            float: The sum of all decay probabilities for the given mother.
        """
        return self.br_manager.calculate_total_decay(mother)
    
    def get_brs(self, mother : int) -> List[Dict[str, Any]]:
        """
        Retrieve all branching ratios for the specified mother particle.

        Args:
            mother: The ID of the mother particle.

        Returns:
            Dict[Tuple[int], float]: A dictionary mapping daughter particle configurations 
            to their branching ratios.
        """
        return self.br_manager.calculate_branching_ratios_for_mother(mother)
    
    def get_br(self, mother : int, daugther : MultiSet[int]):
        """
        Retrieve the branching ratio for a specific decay channel.

        Args:
            mother: The ID of the mother particle.
            daughter: A multiset or iterable of daughter particle IDs.

        Returns:
            float: The branching ratio for the specified decay channel.
        """
        return self.br_manager.calculate_branching_ratio_for_mother(mother, daugther)

    def add_decays(self, decays_list : List, strategy : CalculationDecayStrategy, config : Dict):
        """
        Add multiple decay channels using a specified calculation strategy.

        Args:
            decays_list (List): A list of decay definitions to add.
            strategy (CalculationDecayStrategy): The strategy used to calculate decay probabilities.
            config (Dict): Configuration parameters passed to the strategy.

        Returns:
            None
        """
        self.br_manager.add_decays(decays_list, strategy, config)
        
    def get_all_decays(self, mother : int = None) -> List[Tuple]:
        """
        Retrieve all decay channels, optionally filtered by a specific mother particle.

        Args:
            mother (int, optional): The ID of the mother particle to filter by. 
                If None, returns all decays.

        Returns:
            List[Tuple]: A list of decay tuples (mother, daughters, probability).
        """
        return self.br_manager.get_all_decays(mother)
    
    
    def add_special_lifetime(self, particle : int, value : float, unit : Unit):
        """Set a particular lifetime for a particle, will be used instead of the 1/Total_Width if set.

        Args:
            particle (int): Particle PDG code.
            value (float): The value of the wanted lifetime.
            unit (Unit): The unit in which the lifetime is given.
        """
        self.br_manager.add_special_lifetime(particle, value, unit)
        
        
    def calculate_lifetime(self, particle : int, unit : Unit):
        """Calculate the lifetime for a particle and use the value in _lifetimes instead of the 1/Total_Width if set.

        Args:
            particle (int): Particle PDG code.
            unit (Unit): The unit in which the lifetime is given.
            
            Returns:
            float: The calculated lifetime in the unit precised by the user.
        """
        return self.br_manager.calculate_lifetime(particle, unit)