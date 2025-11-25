from dataclasses import dataclass
from pathlib import Path
from SetAnubis.core.interfaces import SetAnubisInterface

@dataclass
class MadGraphCommandConfig:
    """Configuration data class for MadGraph command card settings.

    Attributes:
        neo_set_anubis (NeoSetAnubis): General Interface of the neo-set-anubis pipeline
        cards_path (Path): Path to the directory containing MadGraph input cards.
        cache (bool, optional): Whether to enable caching. Defaults to False.
        shower (str, optional): Showering method, e.g., "py8" for Pythia8. Defaults to "py8".
        madspin (str, optional): MadSpin activation status. Defaults to "ON".
        model_in_madgraph (str, optional): Explicit model import name for MadGraph. Defaults to "".
    """
    
    neo_set_anubis: SetAnubisInterface
    cache: bool = False
    shower: str = "py8"
    madspin: str = "ON"
    model_in_madgraph : str = ""
