import os
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface, CalculationDecayStrategy

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PY_SCRIPT_PATH = os.path.join(CURRENT_DIR, "TestFiles", "HNL_eq.py")

if __name__ == "__main__":

    nsa = SetAnubisInterface("Assets/UFO/UFO_HNL")
    
    nsa.set_leaf_param("VeN1", 0)
    nsa.set_leaf_param("VtaN1", 0)
    
    nsa.set_leaf_param("VmuN1", 1)
    nsa.set_leaf_param("mN1", 10)
    dm = DecayInterface(nsa)
    
    decay_list = [
        # {"mother": 9900012, "daughters": [-12, 12, 12]},
        {"mother": 9900012, "daughters": [-11, 11, 12]},
        {"mother": 9900012, "daughters": [-11, 11, 14]},
        {"mother": 9900012, "daughters": [-11, 11, 16]},
        {"mother": 9900012, "daughters": [-11, 13, 14]},
        {"mother": 9900012, "daughters": [-13, 11, 12]}
    ]
    
    common_config = {
        "script_path": PY_SCRIPT_PATH
    }
    
    dm.add_decays(decay_list, CalculationDecayStrategy.PYTHON, common_config)
    
    print(dm.get_decay(9900012, [-11, 11, 14]))