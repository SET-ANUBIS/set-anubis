from SetAnubis.core.MadGraph.adapters.input.PythiaCardBuilder import PythiaCardBuilder

if __name__ == "__main__":
    pythia_str = PythiaCardBuilder().serialize()
    
    print("pythia card generated : \n")
    print(pythia_str)