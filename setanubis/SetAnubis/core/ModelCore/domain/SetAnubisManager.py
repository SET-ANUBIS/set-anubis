
from SetAnubis.core.ModelCore.ports.output import IUFOGetter, IParticleJSONProxy
from SetAnubis.core.DataBase.domain.UFOTree import ExpressionTree
from typing import Dict, Any, List
import particle as part

class SetAnubisPortsConfig:
    """
    Port configuration for the Manager ->
    
    Remove coupling between Manager and Adapter. The interface take care of using the right adapters.
    """
    def __init__(self, UFO_getter : IUFOGetter, particle_from_json : IParticleJSONProxy):
        self.ufo_getter_port : IUFOGetter = UFO_getter
        self.particle_from_json_port : IParticleJSONProxy = particle_from_json
        
        
class SetAnubisManager:
    """Main manager class handling model parameters and particles.

    Manages both calculated parameters via an expression tree and their related metadata.

    Attributes:
        _expression_tree (ExpressionTree): Tree structure representing parameter dependencies.
        particles (Dict[int, Dict]): Dictionary of particle properties indexed by PDG codes.
        _evaluated_params (Dict[str, Any]): Evaluated parameter values.
        more_info_params (Dict[str, Dict[str, int]]): Additional metadata for parameters.
    """

    def __init__(
        self,
        ports : SetAnubisPortsConfig,
        base_particles : List[Dict[str, Any]]
    ):
        
        self._expression_tree : ExpressionTree = ports.ufo_getter_port.get()

        if isinstance(base_particles, dict):
            particles_dict: Dict[int, Dict[str, Any]] = base_particles
        else:
            particles_dict = {x["pdg_code"]: x for x in base_particles}

        particles_dict = ports.particle_from_json_port.get_all_particles()

        self.particles = particles_dict

        self._evaluated_params: Dict[str, Dict] = {}
        self.more_info_params: Dict[str, Dict[str, int]] = {}
        self.__add_VCKM()
        self.__add_decay_width()
        self._evaluate_all()
        

    def _evaluate_all(self):
        """Evaluates the entire expression tree and updates parameter values."""
        all_node_names = list(self._expression_tree.nodes.keys())
        expression_tree = self._expression_tree.copy()

        expression_tree.evaluate_partial(all_node_names)

        updated_dict = {}
        for name, node in expression_tree.nodes.items():
            if node.value is not None:
                updated_dict[name] = {"value" : complex(node.value), "lhablock" : node.lha_block, "lhacode" : node.lha_code}
            else:
                updated_dict[name] = None
        self._evaluated_params = updated_dict
      
    def set_leaf_parameter_value(self, name: str, value: float):
        """Updates a leaf parameter value and re-evaluates the expression tree.

        Args:
            name (str): Parameter name to update.
            value (float): New value for the parameter.

        Raises:
            KeyError: If the parameter is not found.
            ValueError: If the parameter is not a leaf node.
        """
        node = self._expression_tree.nodes.get(name)
        if node is None:
            raise KeyError(f"No parameter '{name}' in ExpressionTree.")
        if len(node.dependencies) > 1:
            print(node.expression)
            raise ValueError(f"Parameter '{name}' is not a leaf (it has an expression).")
        node.value = value

        self._evaluate_all()
          
    def get_leaf_parameters(self):
        """Returns the leaf node (with their value) in the tree. """
        self._expression_tree.get_remaining_leaves
        return {x:y.value  for x,y in self._expression_tree.nodes.items() if len(y.dependencies) <1}
    
    def get_parameter_value(self, name: str) -> complex:
        """Returns the evaluated value of a specified parameter.

        Args:
            name (str): Name of the parameter.

        Returns:
            float: Evaluated parameter value.

        Raises:
            KeyError: If the parameter is not found.
            ValueError: If the parameter has not been evaluated.
        """
        if name not in self._evaluated_params:
            raise KeyError(f"No parameter '{name}' in the evaluated dict.")
        val = self._evaluated_params[name]
        if val is None:
            raise ValueError(f"Parameter '{name}' could not be evaluated.")
        return val["value"]

    def get_parameter_expr(self, name: str):
        """Returns the expression of a specified parameter.

        Args:
            name (str): Name of the parameter.

        Returns:
            Node: Expression of the parameters

        Raises:
            KeyError: If the parameter is not found.
        """
        return self._expression_tree.get_value(name)

    def get_all_parameters(self) -> Dict[str, float]:
        """Returns all evaluated parameters.

        Returns:
            Dict[str, float]: Dictionary of parameter names and their evaluated values.
        """
        return dict(self._evaluated_params)

    def get_all_particles(self) -> Dict[int, Dict[str, Any]]:
        """Returns all particle data.

        Returns:
            Dict[int, Dict]: Dictionary of particles indexed by PDG code.
        """
        if type(self.particles) == dict:
            return self.particles
        else:
            return {x["pdg_code"]: x for x in self.particles}
    
    def get_particle(self, pdg_code):
        """Retrieves particle information by PDG code.

        Args:
            pdg_code (int): PDG code of the particle.

        Returns:
            Dict[str, Any]: Dictionary containing particle properties.
        """
        particle = self.particles.get(abs(pdg_code), None)

        if particle is not None:
            p = dict(particle)
            p["pdg_code"] = pdg_code
            p["charge"] = p["charge"] if pdg_code > 0 else -p["charge"]
            return p
        else:
            particle_from_part = part.Particle.from_pdgid(abs(pdg_code))
            
            antiname = ""
            if particle_from_part.charge != 0:
                antiname = part.Particle.from_pdgid(-abs(pdg_code)).name
            else:
                antiname = part.Particle.from_pdgid(abs(pdg_code)).name
                
            if particle_from_part.mass is not None:
                particle = {"name" : particle_from_part.name, "pdg_code" : pdg_code, "antiname" : antiname, "charge" : particle_from_part.charge if pdg_code >0 else -particle_from_part.charge, "spin" : int(2*particle_from_part.J+1), "mass" : complex(particle_from_part.mass)*10**-3}
            else:
                particle = {"name" : particle_from_part.name, "pdg_code" : pdg_code, "antiname" : antiname, "charge" : particle_from_part.charge if pdg_code >0 else -particle_from_part.charge, "spin" : int(2*particle_from_part.J+1), "mass" : complex(0)*10**-3}
            return particle
        
    
    def get_particle_mass(self, pdg_code) -> float:
        """Retrieves particle mass by PDG code.

        Args:
            pdg_code (int): PDG code of the particle.

        Returns:
            float: Mass of the particle.
        """
        param_value = self.get_particle(pdg_code)["mass"]

        if type(param_value) == complex:
            return param_value
        return self.get_parameter_value(param_value).real
    
    def get_particle_mass_name(self, pdg_code) -> str:
        """Retrieves particle mass by PDG code.

        Args:
            pdg_code (int): PDG code of the particle.

        Returns:
            float: Mass of the particle.
        """
        param_value = self.get_particle(pdg_code)["mass"]

        if type(param_value) == complex:
            raise ValueError("No name for particle " + str(pdg_code))
        return param_value
    # def __add_VCKM(self):
    #     self._expression_tree.add_leaf("lamb", 0.22501)
    #     self._expression_tree.add_leaf("A", 0.826)
    #     self._expression_tree.add_leaf("rho", 0.1632)
    #     self._expression_tree.add_leaf("eta", 0.3615)
        
    #     self._expression_tree.add_expression("V_11", "1-0.5*lamb**2")
    #     self._expression_tree.add_expression("V_12", "lamb")
    #     self._expression_tree.add_expression("V_13", "A*lamb**3*(rho-I*eta)")
    #     self._expression_tree.add_expression("V_21", "-lamb")
    #     self._expression_tree.add_expression("V_22", "1-0.5*lamb**2")
    #     self._expression_tree.add_expression("V_23", "A*lamb**2")
    #     self._expression_tree.add_expression("V_31", "A*lamb**3*(1-rho-I*eta)")
    #     self._expression_tree.add_expression("V_32", "-A*lamb**2")
    #     self._expression_tree.add_leaf("V_33", 1.)
        
    def __add_VCKM(self):
        # Paramètres (mêmes noms/valeurs par défaut que chez toi)
        
        self._expression_tree.add_leaf("lamb", 0.22501)
        self._expression_tree.add_leaf("A",    0.826)
        self._expression_tree.add_leaf("rho",  0.1632)
        self._expression_tree.add_leaf("eta",  0.3615)

        # Auxiliaires (symboliques)
        self._expression_tree.add_expression("l2",  "lamb**2")
        self._expression_tree.add_expression("l3",  "lamb**3")

        self._expression_tree.add_expression("s12", "lamb")
        self._expression_tree.add_expression("s23", "A*l2")

        # u13 comme dans le C++ : complex_t(rho, eta) == (rho + i*eta)
        self._expression_tree.add_expression(
            "u13",
            "A*l3*(rho+I*eta)*sqrt(1-(A*l2)**2) / ( sqrt(1-l2) * (1 - (A*l2)**2*(rho+I*eta)) )"
        )
        self._expression_tree.add_expression("s13",   "abs(u13)")
        self._expression_tree.add_expression("expid", "u13/s13")           # e^{iδ}
        self._expression_tree.add_expression("c12",   "sqrt(1 - s12**2)")
        self._expression_tree.add_expression("c23",   "sqrt(1 - s23**2)")
        self._expression_tree.add_expression("c13",   "sqrt(1 - s13**2)")

        # Matrice CKM (paramétrisation standard)
        self._expression_tree.add_expression("V_11", "c12*c13")
        self._expression_tree.add_expression("V_12", "s12*c13")
        self._expression_tree.add_expression("V_13", "s13/expid")          # = s13*e^{-iδ}

        self._expression_tree.add_expression("V_21", "-s12*c23 - c12*s23*s13*expid")
        self._expression_tree.add_expression("V_22", "c12*c23 - s12*s23*s13*expid")
        self._expression_tree.add_expression("V_23", "s23*c13")

        self._expression_tree.add_expression("V_31", "s12*s23 - c12*c23*s13*expid")
        self._expression_tree.add_expression("V_32", "-c12*s23 - s12*c23*s13*expid")
        self._expression_tree.add_expression("V_33", "c23*c13")
        
    def __add_decay_width(self):
        self._expression_tree.add_leaf("G_W",  2.085) #From wikipedia, for MARTY only
        self._expression_tree.add_leaf("G_Z",  2.4955)
        
if __name__ == "__main__":
    print(part.Particle.from_pdgid(543))
    
    