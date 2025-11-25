
from typing import List
from SetAnubis.core.Pythia.domain.pythia_config import PythiaConfig
from SetAnubis.core.Pythia.domain.pythia_cmnd_generator import PythiaCMNDGenerator

class PythiaConfigFactory:
    """
    A factory class for managing and retrieving configurations for different particle types.
    Allows registration of new particle configurations and retrieval based on particle type.

    Attributes:
        particle_config_map (dict): A mapping from particle type names to their corresponding configuration classes.
    """

    @staticmethod
    def generate(configs : List[PythiaConfig]):
        for config in configs:
            PythiaCMNDGenerator.generate(config)