from pathlib import Path
from SetAnubis.core.MadGraph.adapters.input.ParamCardBuilder import ParamCardBuilder

if __name__ == "__main__":
    ufo_path = Path("db/HNL/UFO_HNL")
    param_card = ParamCardBuilder(ufo_path / 'write_param_card.py').serialize()
    
    print("param card generated : \n")
    print(param_card)