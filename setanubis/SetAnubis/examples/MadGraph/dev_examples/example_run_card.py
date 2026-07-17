"""Edit one run-card setting and print the resulting MadGraph card."""

from SetAnubis.core.MadGraph.adapters.input.RunCardBuilder import RunCardBuilder

if __name__ == "__main__":
    # Override only the event count; all other defaults remain unchanged.
    runcard_editor = RunCardBuilder()
    runcard_editor.set("nevents", 2000)
    runcard_str = runcard_editor.serialize()
    
    print("run card generated : \n")
    print(runcard_str)