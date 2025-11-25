from SetAnubis.core.Madgraph.domain.MadGraphCommandConfig import MadGraphCommandConfig
from SetAnubis.core.Madgraph.domain.MadGraphCommandCard import MadGraphCommandCard
from SetAnubis.core.Madgraph.domain.MadGraphWidthCard import MadGraphWidthCard
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface

import os

UFO_HNL_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "..", "..", "Assets", "UFO", "UFO_HNL"))

if __name__ == "__main__":
    
    neo = SetAnubisInterface(UFO_HNL_DIR)
    config = MadGraphCommandConfig(
        neo_set_anubis = neo,
        cache=False,
        shower="py8",
        madspin="ON",
        model_in_madgraph="HeavyN_Majorana_NLO"
    )

    card = MadGraphCommandCard(config)
    card.add_process("generate p p > n1 ell")
    card.set_output_launch("HNL_Condor_CCDY_qqe")
    card.configure_cards()
    card.add_parameter_scan("VeN1", "[1e-6, 1.]")
    card.add_parameter_scan("MN1", "[0.5, 1.0]")

    print(card.serialize())
    
    print(MadGraphWidthCard("models/HeavyN_Majorana_NLO", ["n1"]).generate())