from SetAnubis.core.MadGraph.adapters.input.JobscriptBuilder import JobScriptBuilder, MadGraphCommandConfig
from SetAnubis.core.MadGraph.adapters.input.MadspinCardBuilder import MadSpinCardAdapter
from SetAnubis.core.MadGraph.adapters.input.ParamCardBuilder import ParamCardBuilder
from SetAnubis.core.MadGraph.adapters.input.RunCardBuilder import RunCardBuilder
from SetAnubis.core.MadGraph.adapters.input.PythiaCardBuilder import PythiaCardBuilder
from SetAnubis.core.MadGraph.adapters.output.CardAdapter import CardAdapter, CardType
from pathlib import Path

class GeneralCardInterface:
    def __init__(self, config : MadGraphCommandConfig):
        self.josbscript_builder = JobScriptBuilder(config)
        self.madspin_builder = MadSpinCardAdapter()
        self.param_card= ParamCardBuilder(Path(config.neo_set_anubis.get_ufo_path()) / 'write_param_card.py').serialize()
        self.run_card_builder = RunCardBuilder() 
        self.pythia_builder = PythiaCardBuilder()