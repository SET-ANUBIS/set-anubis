from typing import Dict, Any, Set
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.domain.MartyManager import MartyManager, MartyFileCopyBuilder
class MartyCalculationAdapter(IDecayCalculation):
    
    def __init__(self, neo : SetAnubisInterface, model_name : str = "SM"):
        self.neo = neo
        self.mm = MartyManager(model_name)
        self.builder_marty = MartyFileCopyBuilder()
        
    def calculate(self, mother: int, daughters: Set[int], parameters: Dict[str, float]) -> float:

        self.mm.build_analytic([mother], list(daughters), self.neo, self.builder_marty)
        
        self.mm.launch_analytic([mother], list(daughters))
        
        self.mm.build_numeric([mother], list(daughters), self.neo, self.builder_marty)
        
        result = self.mm.launch_numeric([mother], list(daughters), self.neo)
        return result
