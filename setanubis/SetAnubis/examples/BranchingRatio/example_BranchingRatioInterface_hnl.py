"""Combine Python and CSV decay providers through the branching-ratio interface."""

from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface, CalculationDecayStrategy
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis import assets_dir
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PY_SCRIPT_PATH = os.path.join(CURRENT_DIR, "TestFiles", "test_BR.py")
CSV_FILE_PATH  = os.path.join(CURRENT_DIR, "TestFiles", "test_BR.csv")

if __name__ == "__main__":
    # Load the packaged HNL UFO and register two independent decay providers.
    setanubis = SetAnubisInterface(os.path.join(assets_dir(),"UFO","UFO_HNL"))
    
    setanubis.set_leaf_param("ZERO", 0)
    all_particles = setanubis.get_all_particles()
    all_params = setanubis.get_all_parameters()
    
    br = DecayInterface(setanubis)
    br.add_decays([{"mother" : 25, "daughters" : [24,-24]}], CalculationDecayStrategy.PYTHON, config={"script_path" : PY_SCRIPT_PATH})
    
    decay_list = [
        {"mother": 25, "daughters": [-13, 13]},
        {"mother": 25, "daughters": [22, 22]},
    ]
    common_config = {
        "file_path": CSV_FILE_PATH,
        "varying_params": ["mN1", "VeN1"], 
        "format_type": "csv"
    }
    
    br.add_decays(decay_list, CalculationDecayStrategy.FILE_INTERPOLATION, common_config)
    
    
    # Query individual widths, the total width, and normalized branching ratios.
    gamma_mumu_script = br.get_decay(25, [-13, 13])
    print(f"[SCRIPT PYTHON] Gamma(H->mu+mu-) = {gamma_mumu_script}")

    gamma_gamma_csv = br.get_decay(25, [22, 22])
    print(f"[CSV FILE] Gamma(H->gamma gamma) = {gamma_gamma_csv}")

    total_width = br.get_decay_tot(25)
    print(f"Total width Gamma(H) = {total_width}")

    brs = br.get_brs(25)
    for item in brs:
        print(item)