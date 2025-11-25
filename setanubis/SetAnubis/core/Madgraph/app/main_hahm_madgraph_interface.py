from pathlib import Path
from SetAnubis.core.Madgraph.adapters.output.CardAdapter import CardAdapter, CardType
from SetAnubis.core.Madgraph.adapters.input.JobscriptBuilder import JobScriptBuilder, MadGraphCommandConfig
from SetAnubis.core.Madgraph.adapters.input.RunCardBuilder import RunCardBuilder
from SetAnubis.core.Madgraph.adapters.input.ParamCardBuilder import ParamCardBuilder
from SetAnubis.core.Madgraph.adapters.input.MadGraphInterface import MadgraphInterface
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.Madgraph.domain.MadspinCardBuilder import MadSpinCardBuilder
from SetAnubis.core.Madgraph.adapters.output.MadGraphLocalRunner import MadGraphLocalRunner
import os

UFO_HAHM_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "..", "..", "Assets", "UFO", "HAHM_variableMW_v5_UFO"))
if __name__ == "__main__":
    
    dry_run = True
    
    neo = SetAnubisInterface(UFO_HAHM_DIR)
    ufo_path = Path(UFO_HAHM_DIR)
    param_card = ParamCardBuilder(ufo_path / 'write_param_card.py').serialize()

    runcard_editor = RunCardBuilder()
    runcard_editor.set("nevents", 2000)
    runcard_str = runcard_editor.serialize()

    madspin_str = CardAdapter.get(CardType.MADSPIN)
    builder_madspin = MadSpinCardBuilder.deserialize(madspin_str)
    builder_madspin.add_decay("decay n1 > ell ell vv")
    madspin_str = builder_madspin.serialize()
    
    pythia_str = CardAdapter.get(CardType.PYTHIA8)

    config = MadGraphCommandConfig(
        neo_set_anubis=neo,
        cache=False,
        model_in_madgraph="HAHM_variableMW_v5_UFO",
        shower="py8",
        madspin="ON")
    
    jobcard = JobScriptBuilder(config)
    jobcard.add_process("generate p p > n1 ell # [QCD]")
    jobcard.set_output_launch("HNL_Condor_CCDY_qqe")
    jobcard.configure_cards()
    jobcard.add_auto_width("WN1")
    jobcard.add_parameter_scan("VeN1", "[1e-6, 1.]")
    jobcard.add_parameter_scan("MN1", "[0.5, 1.0]")
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
    
    mlr = MadGraphLocalRunner()
    
    #Error if madgraph is not installed but that's okay
    mg = MadgraphInterface(
        madgraph_runner=mlr,
        jobscript_str=jobscript_str,
        param_card_str=param_card,
        run_card_str=runcard_str,
        pythia_card_str=pythia_str,
        madspin_card_str=madspin_str
    )

    if not dry_run:
        mg.run()
        mg.retrieve_events()