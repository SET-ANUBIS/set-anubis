from SetAnubis.core.Madgraph.domain.MadspinCardBuilder import MadSpinCardBuilder
from SetAnubis.core.Madgraph.adapters.output.CardAdapter import CardAdapter, CardType


if __name__ == "__main__":
    builder_madspin = MadSpinCardBuilder()
    builder_madspin.add_decay("decay n1 > ell ell vv")
    madspin_str = builder_madspin.serialize()
    
    
    print("madspin card generated : \n")
    print(madspin_str)