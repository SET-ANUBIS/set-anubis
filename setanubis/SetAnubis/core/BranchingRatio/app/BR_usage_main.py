from SetAnubis.core.BranchingRatio.domain.DecayChecker import DecayChecker
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.domain.CalculationStrategy import CalculationDecayStrategy
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PY_SCRIPT_PATH = os.path.join(CURRENT_DIR, "TestFiles", "test_BR.py")
CSV_FILE_PATH  = os.path.join(CURRENT_DIR, "TestFiles", "test_BR.csv")

if __name__ == "__main__":
    neosetanubis = SetAnubisInterface("Assets/UFO/UFO_HNL")
    
    neosetanubis.set_leaf_param("ZERO", 0)
    all_particles = neosetanubis.get_all_particles()
    all_params = neosetanubis.get_all_parameters()
    
    br = DecayInterface(neosetanubis)
        
    br.add_decays([{"mother": 25, "daughters": [-12, 12]}],
        strategy=CalculationDecayStrategy.PYTHON,
        config={"script_path": PY_SCRIPT_PATH}
    )
    
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
    
    
    gamma_mumu_script = br.get_decay(25, [-13, 13])
    print(f"[CSV FILE] Gamma(H->mu+mu-) = {gamma_mumu_script}")

    gamma_gamma_csv = br.get_decay(25, [22, 22])
    print(f"[CSV FILE] Gamma(H->gamma gamma) = {gamma_gamma_csv}")

    gamma_gamma_csv = br.get_decay(25, [12, -12])
    print(f"[SCRIPT PYTHON] Gamma(H->nue nuebar) = {gamma_gamma_csv}")
    
    total_width = br.get_decay_tot(25)
    print(f"Total width Gamma(H) = {total_width}")

    brs = br.get_brs(25)
    for item in brs:
        print(item)