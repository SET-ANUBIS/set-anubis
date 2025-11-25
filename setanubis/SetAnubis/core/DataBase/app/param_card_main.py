from SetAnubis.core.DataBase.adapters.ParamCardGeneratorAdapter import ParamCardGeneratorAdapter
from SetAnubis.core.DataBase.adapters.CardGetter import CardGetter, CardType
import os

import os

UFO_HNL_PARAM_CARD = os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "..", "..", "Assets", "UFO", "UFO_HNL", "write_param_card.py"))

if __name__ == "__main__":
    generator = ParamCardGeneratorAdapter(os.path.join(os.path.dirname(__file__), "..", "..", "UFOInterface", "SM_NLO", "write_param_card.py"))
    print(generator.generate())
    print("----------------------------------------------------------------------------------------\n")
    generator = ParamCardGeneratorAdapter(UFO_HNL_PARAM_CARD)
    print(generator.generate())
    
    print("----------------------------------------------------------------------------------------\n")
    
    print(CardGetter.get(CardType.RUNCARD))
    