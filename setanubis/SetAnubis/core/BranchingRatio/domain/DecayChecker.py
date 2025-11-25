from typing import List, Dict, Any
from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.BranchingRatio.domain.IDecayChecker import IDecayChecker
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface

class DecayChecker(IDecayChecker):
    """Class to verify the validity of particle decays based on conservation rules.

    Implements checks such as electric charge conservation for decay processes.
    """
    
    def check_decay_validity(self, 
                             mother_id: int, 
                             daughters_id: MultiSet[int], nsa : SetAnubisInterface) -> bool:
        """Checks validity of a decay process based on conservation laws.

        Currently checks for electric charge conservation.

        Args:
            mother_id (int): PDG ID of the mother particle.
            daughters_id (MultiSet[int]): PDG IDs of daughter particles.
            nsa (NeoSetAnubisInterface): Interface to retrieve particle information.

        Returns:
            bool: True if decay is valid.

        Raises:
            ValueError: If conservation laws (e.g., electric charge) are violated.
        """
        mother_charge = nsa.get_particle_info(mother_id)["charge"]
          
        
        total_charge_daughters = sum(nsa.get_particle_info(d)["charge"] if d > 0 else -nsa.get_particle_info(-d)["charge"] for d in daughters_id)
        if abs(mother_charge - total_charge_daughters) > 1e-9:
            raise ValueError(f"Charge not conserved in decay: mother {mother_id} "
                             f"has charge {mother_charge}, daughters have {total_charge_daughters}.")
        return True
