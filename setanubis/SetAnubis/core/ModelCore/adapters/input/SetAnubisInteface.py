from SetAnubis.core.ModelCore.domain.SetAnubisManager import SetAnubisManager, SetAnubisPortsConfig
from SetAnubis.core.DataBase.domain.UFOTree import Node
from SetAnubis.core.ModelCore.ports.input.IParameterService import IParameterService
from SetAnubis.core.DataBase.adapters.JSONExtractor import JSONExtractor
from SetAnubis.core.ModelCore.adapters.output.UFOGetter import UFOGetter
from SetAnubis.core.ModelCore.adapters.output.ParticlesFromJSONProxy import ParticlesFromJSONProxy
from typing import Dict, Any

class SetAnubisInterface(IParameterService):
    """
    Adapter interface for accessing and modifying model parameters and particle data.

    This class acts as a bridge between external systems (e.g., UI or other services) 
    and the internal `SetAnubisManager`, exposing simplified methods to interact 
    with model parameters and particle information.

    Args:
        ufo_path (str): Path to the UFO (Universal FeynRules Output) model directory.

    Attributes:
        manager (SetAnubisManager): Internal manager handling parameter and particle data logic.
    """

    def __init__(self, ufo_path: str):
        ufo_interface = UFOGetter(ufo_path)
        
        base_particles = ufo_interface.ufo_interface.ufo_manager.get_all_particles(True)

        if isinstance(base_particles, dict):
            particles_dict: Dict[int, Dict[str, Any]] = base_particles
        else:
            particles_dict = {x["pdg_code"]: x for x in base_particles}
            
        proxy = ParticlesFromJSONProxy(
                base_particles=particles_dict,
                extractor=JSONExtractor(),
                json_path="Assets/particles/particleData.json",
                mass_scale=1.0,
                mass_as_complex=True,
            )
            
        set_anubis_port_config = SetAnubisPortsConfig(ufo_interface, proxy)
        self.manager = SetAnubisManager(set_anubis_port_config, base_particles)
        self.ufo_path : str = ufo_path

    def set_leaf_param(self, name: str, value: float):
        """
        Set the value of a leaf parameter in the model.

        Args:
            name (str): The name of the parameter to set.
            value (float): The numerical value to assign to the parameter.

        Returns:
            None
        """
        self.manager.set_leaf_parameter_value(name, value)

    def get_leaf_parameters(self) -> Dict[str, float]:
        """Returns the leaf node (with their value) in the tree. """
        return self.manager.get_leaf_parameters()
    
    def get_ufo_path(self):
        """Returns path to the UFO. """
        return self.ufo_path
    
    def get_parameter_value(self, name: str) -> complex:
        """
        Retrieve the value of a specified parameter.

        Args:
            name (str): The name of the parameter.

        Returns:
            float: The current value of the parameter.
        """
        return self.manager.get_parameter_value(name)

    def get_parameter_expr(self, name: str) -> Node:
        """
        Retrieve the value of a specified parameter.

        Args:
            name (str): The name of the parameter.

        Returns:
            Node: The expression of the parameters (if not leaf).
        """
        return self.manager.get_parameter_expr(name)
    
    def get_all_parameters(self) -> Dict[str, float]:
        """
        Retrieve all parameters available in the model.

        Returns:
            Dict[str, float]: A dictionary mapping parameter names to their current values.
        """
        return self.manager.get_all_parameters()
    
    def get_all_particles(self):
        """
        Retrieve a list of all particles defined in the model.

        Returns:
            List[Dict]: A list of dictionaries, each representing a particle and its properties.
        """
        return self.manager.get_all_particles()
    
    def get_particle_info(self, pdg_code : int):
        """
        Retrieve detailed information about a particle given its PDG code.

        Args:
            pdg_code (int): The PDG (Particle Data Group) code of the particle.

        Returns:
            Dict: A dictionary containing information about the particle (e.g., mass, charge, name).
        """
        return self.manager.get_particle(pdg_code)
    
    def get_particle_mass(self, pdg_code : int):
        """Retrieves particle mass by PDG code.

        Args:
            pdg_code (int): PDG code of the particle.

        Returns:
            float: Mass of the particle.
        """
        return self.manager.get_particle_mass(pdg_code)
    
    def get_particle_mass_name(self, pdg_code : int):
        """Retrieves particle mass by PDG code.

        Args:
            pdg_code (int): PDG code of the particle.

        Returns:
            float: Mass of the particle.
        """
        return self.manager.get_particle_mass_name(pdg_code)
    
if __name__ == "__main__":
    neo = NeoSetAnubisInterface("Assets/UFO/UFO_HNL")
    
    print(neo.get_particle_info(24))
    print(neo.get_particle_mass(24))
    print(neo.get_all_parameters())
    neo2 = NeoSetAnubisInterface("Assets/UFO/SM_HeavyN_CKM_AllMasses_LO")
    print(neo2.get_all_particles() )
