"""Create and print a minimal MadSpin decay card without running MadGraph."""

from SetAnubis.core.MadGraph.domain.MadspinCardBuilder import MadSpinCardBuilder

if __name__ == "__main__":
    # Add one illustrative decay before serializing the in-memory card.
    builder_madspin = MadSpinCardBuilder()
    builder_madspin.add_decay("decay n1 > ell ell vv")
    madspin_str = builder_madspin.serialize()
    
    
    print("madspin card generated : \n")
    print(madspin_str)