from SetAnubis.core.Pythia.adapters.input.cmnd_scan_manager import CMNDScanManager
from SetAnubis.core.Pythia.domain.cmnd_base_generation import CMNDGenerationManager
from SetAnubis.core.Pythia.domain.special_cases import Specials
from SetAnubis.core.Pythia.infrastructure.enums import HardProductionQCDList
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import CalculationDecayStrategy
from SetAnubis.core.Pythia.adapters.input.pythia_run_interface import PythiaRunInterface

if __name__ == "__main__":
    import os
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PY_SCRIPT_PATH = os.path.join(CURRENT_DIR, "TestFiles", "HNL_eq.py")
    PY_SCRIPT_PRODUCTION_PATH = os.path.join(CURRENT_DIR, "TestFiles", "production_eq.py")
    neo = SetAnubisInterface("Assets/UFO/UFO_HNL")

    neo.set_leaf_param("mN1", 0.6)
    dm = DecayInterface(neo)

    decay_list = [
        # {"mother": 9900012, "daughters": [12,-12,12]},
        {"mother": 9900012, "daughters": [-11, 11, 12]},
        {"mother": 9900012, "daughters": [11,-11,14]},
        {"mother": 9900012, "daughters": [11,-11,16]},
        {"mother": 9900012, "daughters": [11,-13,14]},
        {"mother": 9900012, "daughters": [13,-11,12]},
        {"mother": 9900012, "daughters": [111, 12]}
        
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

    manager = CMNDGenerationManager(neo, dm)
    manager.add_custom_line("StringZ:useOldAExtra=off")

    manager.change_tau0max(1000000)
    # manager.add_specials_cases(Specials.TAU0, {9900012 : 50})

    manager.add_hard_production(HardProductionQCDList.HARDQCD_HARD_C_CBAR)

    manager.add_new_particles([9900012])
    # manager.add_custom_line("9900012:new = N1 N1 2 0 0 1.0")
    # manager.add_custom_line("9900012:tauCalc=off")
    # manager.add_custom_line("9900012:tau0=5000")
    manager.add_decay_to_bsm_particles(9900012)
    manager.add_decay_from_bsm_particles(9900012)

    print(manager.serialize())
    output = manager.serialize()
    # output += "9900012:mayDecay=on"
    with open(os.path.join(os.path.dirname(__file__), "TestFiles", "tau0test.cmnd"), "w") as f:
        f.write(output)

    py_interface = PythiaRunInterface(os.path.join(os.path.dirname(__file__), "outputs"), [9900012])

    output_lhe, output_hepmc, output_txt = py_interface.ensure_directories(["lhe", "hepmc", "txt"])
    py_interface.process_file(
        config_file=os.path.join(os.path.dirname(__file__), "TestFiles", "tau0test.cmnd"),
        output_lhe_dir=output_lhe,
        output_hepmc_dir=output_hepmc,
        output_text_dir=output_txt,
        num_events=1,
        suffix="test",
        include_time=True
    )