from pathlib import Path
from SetAnubis.core.Madgraph.adapters.output.CardAdapter import CardAdapter, CardType
from SetAnubis.core.Madgraph.adapters.input.JobscriptBuilder import JobScriptBuilder, MadGraphCommandConfig
from SetAnubis.core.Madgraph.adapters.input.RunCardBuilder import RunCardBuilder
from SetAnubis.core.Madgraph.adapters.input.ParamCardBuilder import ParamCardBuilder
from SetAnubis.core.Madgraph.adapters.input.MadGraphInterface import MadgraphInterface
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.Madgraph.adapters.output.MadGraphLocalRunner import MadGraphLocalRunner
import os

UFO_HNL_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "..", "..", "Assets", "UFO", "UFO_HNL"))

if __name__ == "__main__":
    dry_run = True
    neo = SetAnubisInterface(UFO_HNL_DIR)
    ufo_path = Path(UFO_HNL_DIR)
    param_card = ParamCardBuilder(ufo_path / 'write_param_card.py').serialize()

    runcard_editor = RunCardBuilder()
    runcard_editor.set("nevents", 2000)
    runcard_str = runcard_editor.serialize()

    config = MadGraphCommandConfig(
        neo_set_anubis=neo,
        cache=False,
        model_in_madgraph="SM_HeavyN_CKM_AllMasses_LO",
        shower=None,
        madspin=None)
    
    jobcard = JobScriptBuilder(config)
    jobcard.add_process("compute_widths ta-")
    # jobcard.set_output_launch("test")
    jobcard.configure_cards()
    jobscript_str = jobcard.serialize()

    print("------------------------------------------------------------------------------------------")
    print(jobscript_str)

    print("------------------------------------------------------------------------------------------")
    
    print(runcard_str)
    print("------------------------------------------------------------------------------------------")
    
    print(param_card)
    print("------------------------------------------------------------------------------------------")
    
    mrl = MadGraphLocalRunner()
    mg = MadgraphInterface(
        madgraph_runner=mrl,
        jobscript_str=jobscript_str,
        param_card_str=param_card,
        run_card_str=runcard_str
    )

    if not dry_run:
        mg.run()
        mg.retrieve_events(width_mode=True)
