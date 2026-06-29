from pathlib import Path
from SetAnubis.core.MadGraph.adapters.input.ParamCardBuilder import ParamCardBuilder
from SetAnubis.resources import ufo_path

if __name__ == "__main__":
    hnl_ufo_path = ufo_path("UFO_HNL")

    param_card = ParamCardBuilder(hnl_ufo_path / 'write_param_card.py').serialize()
    
    print("param card generated : \n")
    print(param_card)