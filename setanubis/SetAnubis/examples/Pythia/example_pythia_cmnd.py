from SetAnubis.core.Pythia.adapters.input.pythia_cmnd_interface import PythiaCMNDInterface
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import CalculationDecayStrategy
from SetAnubis.core.Pythia.infrastructure.enums import HardProductionQCDList
import os
from pathlib import Path

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PY_SCRIPT_PATH = os.path.join(CURRENT_DIR, "TestFiles", "HNL_eq.py")
PY_SCRIPT_PRODUCTION_PATH = os.path.join(CURRENT_DIR, "TestFiles", "production_eq.py")

if __name__ == "__main__":
    
    nsa = SetAnubisInterface("db/HNL/UFO_HNL")
    nsa.set_leaf_param("mN1", 1.0)
    
    dm = DecayInterface(nsa)
    
    decay_list = [
        {"mother": 9900012, "daughters": [12,-12,12]},
        {"mother": 9900012, "daughters": [-11, 11, 12]},
        {"mother": 9900012, "daughters": [11,-11,14]},
        {"mother": 9900012, "daughters": [11,-11,16]},
        {"mother": 9900012, "daughters": [11,-13,14]},
        {"mother": 9900012, "daughters": [13,-11,12]}
        
    ]

    decay_prod_list = [
        {"mother": 4132, "daughters": [9900012, -11, 3312]},
        {"mother": 4132, "daughters": [9900012, -13, 3312]},
        {"mother": 421, "daughters": [9900012, -11, -321]},
        {"mother": 421, "daughters": [9900012, -11, -323]},
        {"mother": 421, "daughters": [9900012, -13, -321]}        
    ]
    
    common_config = {
        "script_path": PY_SCRIPT_PATH
    }
    
    production_config = {
        "script_path": PY_SCRIPT_PRODUCTION_PATH
    }
    
    dm.add_decays(decay_list, CalculationDecayStrategy.PYTHON, common_config)
    
    dm.add_decays(decay_prod_list, CalculationDecayStrategy.PYTHON, production_config)

    command = PythiaCMNDInterface(nsa, dm)
    
    command.change_sm_particles([4132], Path(os.path.dirname(os.path.abspath(__file__)) + "/TestFiles" + "/sm_particles_changes.yaml"))
    command.add_new_particles([9900012])
    
    command.add_hard_production(HardProductionQCDList.HARDQCD_HARD_C_CBAR)
    command.add_hard_production(HardProductionQCDList.HARDQCD_HARDB_B_BAR)
    
    command.add_decay_to_bsm_particles(9900012)
    # command.add_new_particles([{"name" : "N1", "antiname" : "N1", "code" : 9900012, "charge" : 0, "spin" : 2, "color" : 0, "mass" : 1.0, "tau0" : 100000}])
    
    
    # command.add_decay_from_bsm_particles({9900012: {(11,-11,12) : 0.4}})
    command.add_decay_from_bsm_particles(9900012)
    
    print("CMND generated : \n")
    print(command.serialize())