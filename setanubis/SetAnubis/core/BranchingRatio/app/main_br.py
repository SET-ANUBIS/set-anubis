from SetAnubis.core.BranchingRatio.adapters.output.BRCalculatorLoader import BRCalculatorLoader
import os

if __name__ == "__main__":
    br_calculator = BRCalculatorLoader.load_calculator(os.path.join("/".join(__file__.split("/")[:-1]), "TestFiles/BRCalculatorExample.py"))
    print(br_calculator.calculate(23, [2,-2], {"x": 5}))