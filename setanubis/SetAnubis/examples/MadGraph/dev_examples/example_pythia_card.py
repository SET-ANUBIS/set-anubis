"""Create and print the default Pythia shower card used by MadGraph."""

from SetAnubis.core.MadGraph.adapters.input.PythiaCardBuilder import PythiaCardBuilder

if __name__ == "__main__":
    # Serialize the default shower settings without creating any files.
    pythia_str = PythiaCardBuilder().serialize()
    
    print("pythia card generated : \n")
    print(pythia_str)