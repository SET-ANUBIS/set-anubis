from typing import Protocol
from SetAnubis.core.Common.MultiSet import MultiSet

class IBranchingRatioCalculator(Protocol):
    def get(self, br_type: str, mother_particle : int, daughters_particles : MultiSet) -> float:
        """Mandatory method to get the BR value.
        
        Args:
            br_type (str): Type of BR ("Total BR", "BR", "Width").
            br_type (str): Type of BR ("Total BR", "BR", "Width").
            br_type (str): Type of BR ("Total BR", "BR", "Width").
        
        Returns:
            float: BR value calculated.
        """
        ...
