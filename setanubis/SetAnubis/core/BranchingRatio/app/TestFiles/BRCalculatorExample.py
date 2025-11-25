from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation, MultiSet, Dict

class MyBR(IDecayCalculation):
    def calculate(self, 
                  mother: int, 
                  daughters: MultiSet[int], 
                  parameters: Dict[str, float]) -> float:
        return 0.5

