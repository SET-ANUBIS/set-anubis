from pathlib import Path
from SetAnubis.core.Madgraph.adapters.input.JobscriptBuilder import JobScriptBuilder, MadGraphCommandConfig
from SetAnubis.core.Madgraph.adapters.input.RunCardBuilder import RunCardBuilder
from SetAnubis.core.Madgraph.adapters.input.ParamCardBuilder import ParamCardBuilder
from SetAnubis.core.Madgraph.adapters.input.MadGraphInterface import MadgraphInterface
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.Madgraph.adapters.input.MadspinCardBuilder import MadSpinCardBuilder
from SetAnubis.core.Madgraph.adapters.input.PythiaCardBuilder import PythiaCardBuilder

from SetAnubis.core.Madgraph.adapters.output.MadGraphDockerRunner import MadGraphDockerRunner
import os

UFO_HNL_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "..", "..", "Assets", "UFO", "UFO_HNL"))

if __name__ == "__main__":
    print(UFO_HNL_DIR)
    
    dry_run = True
    
    neo = SetAnubisInterface(UFO_HNL_DIR)
    ufo_path = Path(UFO_HNL_DIR)
    param_card = ParamCardBuilder(ufo_path / 'write_param_card.py').serialize()

    runcard_editor = RunCardBuilder()
    runcard_editor.set("nevents", 2000)
    runcard_str = runcard_editor.serialize()

    builder_madspin = MadSpinCardBuilder()
    builder_madspin.add_decay("decay n1 > ell ell vv")
    madspin_str = builder_madspin.serialize()
    
    pythia_str = PythiaCardBuilder().serialize()

    config = MadGraphCommandConfig(
        neo_set_anubis=neo,
        cache=False,
        model_in_madgraph="SM_HeavyN_CKM_AllMasses_LO",
        shower="py8",
        madspin="ON")
    
    jobcard = JobScriptBuilder(config)
    jobcard.add_process("generate p p > n1 ell # [QCD]")
    # jobcard.add_special_section(CommandSectionType.SETTINGS,"set nb_core -1")
    jobcard.set_output_launch("HNL_Condor_CCDY_qqe")
    jobcard.configure_cards()
    jobcard.add_auto_width("WN1")
    jobcard.add_parameter_scan("VeN1", "[1.]")
    jobcard.add_parameter_scan("mN1", "[1.0]")
    jobscript_str = jobcard.serialize()

    print("------------------------------------------------------------------------------------------")
    print(jobscript_str)
    print("------------------------------------------------------------------------------------------")
    print(madspin_str)
    print("------------------------------------------------------------------------------------------")
    print(pythia_str)
    print("------------------------------------------------------------------------------------------")
    
    print(runcard_str)
    print("------------------------------------------------------------------------------------------")
    
    print(param_card)
    print("------------------------------------------------------------------------------------------")
    
    runner = MadGraphDockerRunner()
    
    #Error if madgraph is not installed but that's okay
    mg = MadgraphInterface(
        madgraph_runner=runner,
        jobscript_str=jobscript_str,
        param_card_str=param_card,
        run_card_str=runcard_str,
        pythia_card_str=pythia_str,
        madspin_card_str=madspin_str
    )

    if not dry_run:
        mg.run()
        mg.retrieve_events()
