from SetAnubis.core.Pythia.adapters.input.cmnd_scan_manager import CMNDScanManager
from SetAnubis.core.Pythia.infrastructure.enums import HardProductionQCDList
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import CalculationDecayStrategy
from SetAnubis.core.Pythia.adapters.input.pythia_run_interface import PythiaRunInterface
import numpy as np
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PY_SCRIPT_PATH = os.path.join(CURRENT_DIR, "TestFiles", "HNL_eq.py")
PY_SCRIPT_PRODUCTION_PATH = os.path.join(CURRENT_DIR, "TestFiles", "production_eq.py")


if __name__ == "__main__":
    
    
    nsa = SetAnubisInterface("Assets/UFO/UFO_HNL")
    
    nsa.set_leaf_param("VmuN1", 0)
    nsa.set_leaf_param("VtaN1", 0)
    
    dm = DecayInterface(nsa)
    
    decay_list = [
        # {"mother": 9900012, "daughters": [-12, 12, 12]},
        {"mother": 9900012, "daughters": [-11, 11, 12]},
        {"mother": 9900012, "daughters": [-11, 11, 14]},
        {"mother": 9900012, "daughters": [-11, 11, 16]},
        {"mother": 9900012, "daughters": [-11, 13, 14]},
        {"mother": 9900012, "daughters": [-13, 11, 12]},
        {"mother": 9900012, "daughters": [111, 12]},
        {"mother": 9900012, "daughters": [111, 14]},
        {"mother": 9900012, "daughters": [111, 16]},
        {"mother": 9900012, "daughters": [211, 11]},
        {"mother": 9900012, "daughters": [-13, 13, 12]},
        {"mother": 9900012, "daughters": [-13, 13, 14]},
        {"mother": 9900012, "daughters": [-13, 13, 16]},
        {"mother": 9900012, "daughters": [211, 13]},
        {"mother": 9900012, "daughters": [221, 12]},
        {"mother": 9900012, "daughters": [221, 14]},
        {"mother": 9900012, "daughters": [221, 16]},
        {"mother": 9900012, "daughters": [113, 12]},
        {"mother": 9900012, "daughters": [113, 14]},
        {"mother": 9900012, "daughters": [113, 16]},
        {"mother": 9900012, "daughters": [213, 11]},
        {"mother": 9900012, "daughters": [223, 12]},
        {"mother": 9900012, "daughters": [223, 14]},
        {"mother": 9900012, "daughters": [223, 16]},
        {"mother": 9900012, "daughters": [213, 13]},
        {"mother": 9900012, "daughters": [331, 12]},
        {"mother": 9900012, "daughters": [331, 14]},
        {"mother": 9900012, "daughters": [331, 16]},
        {"mother": 9900012, "daughters": [333, 12]},
        {"mother": 9900012, "daughters": [333, 14]},
        {"mother": 9900012, "daughters": [333, 16]},
        {"mother": 9900012, "daughters": [-11, 15, 16]},
        {"mother": 9900012, "daughters": [-15, 11, 12]},
        {"mother": 9900012, "daughters": [-13, 15, 16]},
        {"mother": 9900012, "daughters": [-15, 13, 14]},
        {"mother": 9900012, "daughters": [431, 11]},
        {"mother": 9900012, "daughters": [431, 13]},
        {"mother": 9900012, "daughters": [433, 11]},
        {"mother": 9900012, "daughters": [433, 13]},
        {"mother": 9900012, "daughters": [441, 12]},
        {"mother": 9900012, "daughters": [441, 14]},
        {"mother": 9900012, "daughters": [441, 16]},
    ]
    
    parts = nsa.get_all_particles()

    decay_prod_list = [
        {"mother": 4132, "daughters": [9900012, -11, 3312]},
        {"mother": 4132, "daughters": [9900012, -13, 3312]},
        {"mother": 421, "daughters": [9900012, -11, -321]},
        {"mother": 421, "daughters": [9900012, -11, -323]},
        {"mother": 421, "daughters": [9900012, -13, -321]},
        {"mother": 431, "daughters": [9900012, -13, 221]},
        {"mother": 431, "daughters": [9900012, -11, 221]},
        {"mother": 431, "daughters": [9900012, -15, 221]},
        {"mother": 431, "daughters": [9900012, -11, 221]},
        {"mother": 431, "daughters": [9900012, -13, 221]},
        {"mother": 4122, "daughters": [9900012, -11, 3122]},
        {"mother": 4122, "daughters": [9900012, -13, 3122]},
        {"mother": 411, "daughters": [9900012, -13]},
        {"mother": 411, "daughters": [9900012, -11]},
        {"mother": 411, "daughters": [9900012, -15]},
        {"mother": 411, "daughters": [9900012, -11, -311]},
        {"mother": 411, "daughters": [9900012, -13, -311]},
        {"mother": 411, "daughters": [9900012, -11, -313]},
        {"mother": 411, "daughters": [9900012, -13, -313]},
    ]
    
    common_config = {
        "script_path": PY_SCRIPT_PATH
    }
    
    production_config = {
        "script_path": PY_SCRIPT_PRODUCTION_PATH,
        "BR" : True
    }
    
    dm.add_decays(decay_list, CalculationDecayStrategy.PYTHON, common_config)
    
    dm.add_decays(decay_prod_list, CalculationDecayStrategy.PYTHON, production_config)
    
    scan = CMNDScanManager(nsa, dm, os.path.join(os.path.dirname(__file__), "scan_cmnd_files"))
    
    
    liste_c_masses= []
    for x in np.arange(0.2, 1.8, 0.2):
        liste_c_masses.append(round(x, 2))
    print(liste_c_masses)
    scan.register_scan("mN1", liste_c_masses)
    scan.register_scan("VeN1", [1.0, 0.1, 0.01, 0.001, 0.0001, 0.00001, 0.000001])
    # scan.register_scan("mN1", [0.8])
    # scan.register_scan("VeN1", [0.001])
    scan.set_new_particle(9900012)
    # scan.set_sm_changes([13],os.path.join(os.path.dirname(__file__), "TestFiles", "modified_muon.yaml") )
    scan.add_decay_from_bsm(9900012)
    scan.add_decay_to_bsm(9900012)
    scan.set_production(HardProductionQCDList.HARDQCD_HARD_C_CBAR)

    scan.generate_all_cmnds()

    py_interface = PythiaRunInterface(os.path.join(os.path.dirname(__file__), "outputs"), [9900012])

    output_lhe, output_hepmc, output_text = py_interface.ensure_directories(["lhe", "hepmc", "text"])
    liste_cmnd = os.listdir(os.path.join(os.path.dirname(__file__), "scan_cmnd_files"))
    liste_cmnd_path = []
    for x in liste_cmnd:
        liste_cmnd_path.append(os.path.join(os.path.dirname(__file__), "scan_cmnd_files", x))
    
    for pat in liste_cmnd_path:
            
        py_interface.process_file(
            config_file=pat,
            output_lhe_dir=output_lhe,
            output_hepmc_dir=output_hepmc,
            output_text_dir=output_text,
            num_events=2000,
            suffix="test",
            include_time=True
        )