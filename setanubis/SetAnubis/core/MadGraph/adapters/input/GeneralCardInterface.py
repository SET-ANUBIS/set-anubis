from SetAnubis.core.MadGraph.adapters.input.JobscriptBuilder import JobScriptBuilder, MadGraphCommandConfig
from SetAnubis.core.MadGraph.adapters.input.MadspinCardBuilder import MadSpinCardAdapter
from SetAnubis.core.MadGraph.adapters.input.ParamCardBuilder import ParamCardBuilder
from SetAnubis.core.MadGraph.adapters.input.RunCardBuilder import RunCardBuilder
from SetAnubis.core.MadGraph.adapters.input.PythiaCardBuilder import PythiaCardBuilder
from SetAnubis.core.MadGraph.adapters.output.CardAdapter import CardAdapter, CardType
from pathlib import Path

class GeneralCardInterface:
    def __init__(self, config: MadGraphCommandConfig):
        # Historical typo kept as an alias for backward compatibility.
        # New examples and documentation should use `jobscript_builder`.
        self.jobscript_builder: JobScriptBuilder = JobScriptBuilder(config)
        self.josbscript_builder: JobScriptBuilder = self.jobscript_builder
        self.madspin_builder: MadSpinCardAdapter = MadSpinCardAdapter()
        self.param_card: str = ParamCardBuilder(Path(config.neo_set_anubis.get_ufo_path()) / 'write_param_card.py').serialize()
        self.run_card_builder: RunCardBuilder = RunCardBuilder()
        self.pythia_builder: PythiaCardBuilder = PythiaCardBuilder()