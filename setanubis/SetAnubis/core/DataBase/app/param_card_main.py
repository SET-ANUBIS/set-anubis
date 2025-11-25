from SetAnubis.core.DataBase.adapters.ParamCardGeneratorAdapter import ParamCardGeneratorAdapter
from SetAnubis.core.DataBase.adapters.CardGetter import CardGetter, CardType
import os

if __name__ == "__main__":
    generator = ParamCardGeneratorAdapter(os.path.join(os.path.dirname(__file__), "..", "..", "UFOInterface", "SM_NLO", "write_param_card.py"))
    print(generator.generate())
    print("----------------------------------------------------------------------------------------\n")
    generator = ParamCardGeneratorAdapter('Assets/UFO/UFO_HNL/write_param_card.py')
    print(generator.generate())
    
    print("----------------------------------------------------------------------------------------\n")
    
    print(CardGetter.get(CardType.RUNCARD))
    