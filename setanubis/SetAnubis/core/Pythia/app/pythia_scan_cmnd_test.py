from SetAnubis.core.Pythia.adapters.input.cmnd_scan_manager import CMNDScanManager
from SetAnubis.core.Pythia.infrastructure.enums import HardProductionQCDList
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import CalculationDecayStrategy

import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PY_SCRIPT_PATH = os.path.join(CURRENT_DIR, "TestFiles", "HNL_eq.py")
PY_SCRIPT_PRODUCTION_PATH = os.path.join(CURRENT_DIR, "TestFiles", "production_eq.py")


if __name__ == "__main__":
    
    
    nsa = SetAnubisInterface("Assets/UFO/UFO_HNL")
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
    
    scan = CMNDScanManager(nsa, dm, os.path.join(os.path.dirname(__file__), "scan_cmnd_files"))
    scan.register_scan("mN1", [0.5, 1.0, 2.0])
    scan.register_scan("VeN1", [1e-9, 5e-9])
    scan.set_new_particle(9900012)
    scan.set_sm_changes([13],os.path.join(os.path.dirname(__file__), "TestFiles", "modified_muon.yaml") )
    scan.add_decay_from_bsm(9900012)
    scan.add_decay_to_bsm(9900012)
    scan.set_production(HardProductionQCDList.HARDQCD_HARD_C_CBAR)

    scan.generate_all_cmnds()
