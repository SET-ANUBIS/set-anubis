from SetAnubis.core.Madgraph.adapters.input.RunCardBuilder import RunCardBuilder

if __name__ == "__main__":
    runcard_editor = RunCardBuilder()
    runcard_editor.set("nevents", 2000)
    runcard_str = runcard_editor.serialize()
    
    print("run card generated : \n")
    print(runcard_str)