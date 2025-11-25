from SetAnubis.core.MadGraph.adapters.input.GeneralCardInterface import GeneralCardInterface, MadGraphCommandConfig
from SetAnubis.core.MadGraph.adapters.input.MadGraphInterface import MadgraphInterface
from SetAnubis.core.interfaces import SetAnubisInterface

if __name__ == "__main__":

    """
    Paramater use to choose if we want to produce the card only (True) or run madgraph on docker.
    """
    dry_run = True
    
    """
    General interface of the neo-set-anubis pipeline. Need the path to the UFO as an input.
    
    Everything concerning this interface is available in the ModelCore.exampleNeoSetAnubisInterface.py example.
    """
    neo = SetAnubisInterface("db/HNL/UFO_HNL")
    
    """
    Configuration for the MagraphInterface (for writing cards). Few inputs are needed :
    
        -   neo_set_anubis : General NeoSetAnubis interface, with the ufo_path and all the particles/parameters.
        -   cards_path  :   Path to the cards in the docker container. No need to change it it will only break things (or be sure of what you're doing !).
        -   cache : If we want to use what's already in MadGraph, Generally put it to False only you're sure or doing the same scan than before.
        -   model_in_madgraph : name of the UFO, used in madgraph to import the model (from Feynrule).
        -   shower  :   shower option in madgraph, tell it which software will deal with the shower (use pythia by default).
        -   madspin :   madspin option, whether to use it for the decay of the LLP or not.
    """
    config = MadGraphCommandConfig(
        neo_set_anubis=neo,
        cache=False,
        model_in_madgraph="SM_HeavyN_CKM_AllMasses_LO",
        shower="py8",
        madspin="ON")
    
    """
    General interface for the cards creation. Everything on the heap, no file writing or anything.
    
    The three main cards are the runcard, param_card and the jobcard.
    
    param_card : The param_card is automatically created by the UFO (writing part) and will use the default value of the parameters. In order to change a parameters value, either change it in the UFO or 
    in the jobscard (parameter scan can be used with one value to set the parameters's value).
    
    run_card : The run_card can be edited to change the number of events, the parton distribution function, the energy of the beam, some cuts or other general parameters.
    
    jobcard : The jobcard is used to select the differents process to generate the LLP, and choose the parameters for the scan. See below the example.
    
    Two other cards are used for madspin and pythia : 
    
    pythia_card : The pythia_card is automatically generated and shouldn't be changed
    """
    card_interface = GeneralCardInterface(config)
    
    param_card = card_interface.param_card

    runcard_editor = card_interface.run_card_builder
    runcard_editor.set("nevents", 2000)
    runcard_str = runcard_editor.serialize()

    builder_madspin = card_interface.madspin_builder
    builder_madspin.add_decay("decay n1 > ell ell vv")
    madspin_str = builder_madspin.serialize()
    
    pythia_str = card_interface.pythia_builder.serialize()

    
    jobcard = card_interface.josbscript_builder
    jobcard.add_process("generate p p > n1 ell # [QCD]")
    jobcard.set_output_launch("HNL_Condor_CCDY_qqe")
    jobcard.configure_cards()
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
    
    if not dry_run:
        mg = MadgraphInterface(
            jobscript_str=jobscript_str,
            param_card_str=param_card,
            run_card_str=runcard_str,
            pythia_card_str=pythia_str,
            madspin_card_str=madspin_str
        )

        mg.run()
        mg.retrieve_events()
