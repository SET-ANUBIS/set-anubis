import os
import ast
from typing import List, Dict, Any

from SetAnubis.core.DataBase.adapters.UFOParser import UFOParser
from SetAnubis.core.DataBase.domain.UFOTree import ExpressionTree
from SetAnubis.core.Common.MultiSet import MultiSet

SM_PARAMETERS = {
    "MASS" : [1,2,3,4,5,6,11,12,13,14,15,16,23,24,25],
    "CKMBLOCK" : [1],
    "SMINPUTS" : [1,2,3,4],
    "YUKAWA" : [1,2,3,4,5,6],
    "DECAY" : [23,24, 6, 25],
    "GAUGEMASS" : [1],
    "HIGGS" : [1]
}

class UFOManager:
    """
    Manages the extraction and processing of particle and parameter data from a UFO model.
    
    Attributes:
        ufo_folder (str): Path to the UFO model folder.
        sm (str): Path to the Standard Model (SM) reference data.
    """
    def __init__(self, ufo_folder_path):
        """
        Retrieves all particles defined in the UFO model.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing particle names and PDG codes.
        """
        self.ufo_folder = ufo_folder_path
        self.sm = os.path.join("/".join(__file__.split("/")[:-1]), "..", "..", "UFOInterface", "SM_NLO")


    def get_all_particles(self, more_infos = False) -> List[Dict[str, Any]]:
        """
        Retrieves all particles defined in the UFO model.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing particle names and PDG codes.
        """
        all_part_obj = UFOParser.parse(os.path.join(self.ufo_folder, "particles.py"))
        if more_infos:
            all_part = [{"name": x.get("name"),"pdg_code" : x.get("pdg_code"), "antiname" : x.get("antiname"), "charge" : x.get("charge"), "color" : x.get("color"), "spin" : x.get("spin"), "mass" : x.get("mass")} for x in all_part_obj]
        else:
            all_part = [{"name": x.get("name"),"pdg_code" : x.get("pdg_code")} for x in all_part_obj]
        return all_part

    def get_new_particles(self, more_infos = False) -> List[Dict[str, Any]]:
        """
        Retrieves particles that are not part of the Standard Model.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing names and PDG codes of new particles.
        """
        sm_part_obj = UFOParser.parse(os.path.join(self.sm, "particles.py"))
        all_part_obj = UFOParser.parse(os.path.join(self.ufo_folder, "particles.py"))
        sm_part = [{"name": x.get("name"),"pdg_code" : x.get("pdg_code")} for x in sm_part_obj]
        if more_infos:
            all_part = [{"name": x.get("name"),"pdg_code" : x.get("pdg_code"), "antiname" : x.get("antiname"), "charge" : x.get("charge"), "color" : x.get("color"), "spin" : x.get("spin")} for x in all_part_obj]
        else:
            all_part = [{"name": x.get("name"),"pdg_code" : x.get("pdg_code")} for x in all_part_obj]
        sm_codes = [x["pdg_code"] for x in sm_part]
        if more_infos:
            new_part = [{"name": x.get("name"),"pdg_code" : x.get("pdg_code"), "antiname" : x.get("antiname"), "charge" : x.get("charge"), "color" : x.get("color"), "spin" : x.get("spin")} for x in all_part if x["pdg_code"] not in sm_codes]
        else:
            new_part = [{"name": x.get("name"),"pdg_code" : x.get("pdg_code")} for x in all_part if x["pdg_code"] not in sm_codes]

        return new_part
    
    def get_sm_particles(self, more_infos = False) -> List[Dict[str, Any]]:
        """
        Retrieves particles that belong to the Standard Model.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing names and PDG codes of SM particles.
        """
        sm_part_obj = UFOParser.parse(os.path.join(self.sm, "particles.py"))

        if more_infos:
            sm_part = [{"name": x.get("name"),"pdg_code" : x.get("pdg_code"), "antiname" : x.get("antiname"), "charge" : x.get("charge"), "color" : x.get("color"), "spin" : x.get("spin")} for x in sm_part_obj]
        else:
            sm_part = [{"name": x.get("name"),"pdg_code" : x.get("pdg_code")} for x in sm_part_obj]
        return sm_part

    def get_params(self) -> List[Dict[str, Any]]:
        """
        Retrieves all parameters defined in the UFO model.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing parameter names, blocks, PDG codes, and values.
        """
        all_parameters = UFOParser.parse(os.path.join(self.ufo_folder, "parameters.py"))
        all_params = [{"name": x.get("name"), "block" : x.get("lhablock"), "pdgcode" : x.get("lhacode"), "value" : x.get("value")} for x in all_parameters]
        return all_params

    def clean_expression(self, expression_str: str) -> str:
        """
        Cleans mathematical expressions by replacing `cmath` functions with their SymPy equivalents.
        
        Args:
            expression_str (str): The mathematical expression as a string.
        
        Returns:
            str: The cleaned expression.
        """
        replacements = {
            "cmath.pi": "pi", "cmath.sqrt": "sqrt", "cmath.cos": "cos",
            "cmath.sin": "sin", "cmath.tan": "tan", "cmath.acos": "acos",
            "cmath.asin": "asin", "cmath.atan": "atan", "cmath.exp": "exp",
            "cmath.log": "log", "complex(0,1)": "I"
        }
        for old, new in replacements.items():
            expression_str = expression_str.replace(old, new)
        return expression_str
    
    def __extend_particles(self, particules):
        extended_particles_code = []
        for particle in particules:
            name, pdg = particle["name"], particle["pdg_code"]
            extended_particles_code.append(particle)

            if "+" in name or "-" in name:
                if "+" in name:
                    antiparticle_name = name.replace("+", "-")
                    antiparticle_variant = antiparticle_name.replace("-", "__minus__")
                    variant_name = name.replace("+", "__plus__")
                else:
                    antiparticle_name = name.replace("-", "+")
                    antiparticle_variant = antiparticle_name.replace("+", "__plus__")
                    variant_name = name.replace("-", "__minus__")

                extended_particles_code.append({"name": antiparticle_name, "pdg_code": -pdg})

                extended_particles_code.append({"name": variant_name, "pdg_code": pdg})
                extended_particles_code.append({"name": antiparticle_variant, "pdg_code": -pdg})
            else:
                antiparticle_name = name.replace(name, name+"__tilde__")
                extended_particles_code.append({"name": antiparticle_name, "pdg_code": -pdg})
        name_to_pdg = {particle['name']: particle['pdg_code'] for particle in extended_particles_code}

        return name_to_pdg
    
    def get_decays(self) -> Dict[str, Dict[MultiSet, str]]:
        """
        Extracts decay equations from the UFO model.
        
        Returns:
            Dict[str, Dict[tuple, str]]: A dictionary mapping particle names to their decay equations.
        """
        decay_path = os.path.join(self.ufo_folder, "decays.py")
        if not os.path.exists(decay_path):
            raise FileNotFoundError(f"Decay file {decay_path} not found.")
        
        with open(decay_path, 'r') as file:
            content = file.read()
        
        tree = ast.parse(content)
        decays = {}
        particles_code = self.get_all_particles()
        name_to_pdg = self.__extend_particles(particles_code)

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                func_name = getattr(node.value.func, 'id', None)
                if func_name == 'Decay':
                    args = {kw.arg: kw.value for kw in node.value.keywords}
                    particle_name = args['particle'].attr if 'particle' in args else None
                    partial_widths = args['partial_widths'] if 'partial_widths' in args else None
                    if particle_name and isinstance(partial_widths, ast.Dict):
                        decay_dict = {}
                        for key, value in zip(partial_widths.keys, partial_widths.values):
                            if isinstance(key, ast.Tuple):
                                daughters = MultiSet(k.attr for k in key.elts)
                                daughters = MultiSet(name_to_pdg[name] for name in daughters if name in name_to_pdg)
                                equation = ast.unparse(value)
                                equation = self.clean_expression(equation)
                                decay_dict[daughters] = equation.replace("'", "")
                        decays[name_to_pdg[particle_name]] = decay_dict
        
        return decays
    
    def get_decays_from_new_particles(self) -> Dict[str, Dict[MultiSet, str]]:
        """
        Extracts decay equations only for new particles beyond the Standard Model.
        
        Returns:
            Dict[str, Dict[tuple, str]]: A dictionary containing decays of new particles.
        """
        decays = self.get_decays()
        new_particles = self.get_new_particles()
        new_particles = [x["pdg_code"] for x in new_particles]
        new_decays = dict()
        for particle, decays in decays.items():
            if particle in new_particles:
                new_decays[particle] = decays
        return new_decays

    def get_decays_to_new_particles(self) -> Dict[str, Dict[MultiSet, str]]:
        """
        Extracts decay equations where at least one decay product is a new particle.
        
        Returns:
            Dict[str, Dict[tuple, str]]: A dictionary containing decays involving new particles.
        """
        decays_all = self.get_decays()
        new_particles = self.get_new_particles()
        new_particles = [x["pdg_code"] for x in new_particles]
        new_decays = dict()
        for particle, decays in decays_all.items():
            decays_to_new = dict()
            for daughters, equation in decays.items():
                for daugther in daughters:
                    if daugther in new_particles:
                        decays_to_new[daughters] = equation
                        break
            if len(decays_to_new)>0:
                new_decays[particle] = decays_to_new
        return new_decays


    def get_sm_params(self) -> List[Dict[str, Any]]:
        """
        Retrieves Standard Model parameters from the UFO model.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing SM parameters.
        """
        param = self.get_params()
        sm = []
        for paramm in param:
            block = paramm["block"]
            pdgcode = paramm["pdgcode"]
            value = paramm["value"]
            if (block in SM_PARAMETERS and any(code in SM_PARAMETERS[block] for code in pdgcode) and type(value) != str):
                sm.append(paramm)
            
        return sm
    
    def get_param_tree(self) -> ExpressionTree:
        """
        Builds an expression tree from the UFO model parameters.
        
        Returns:
            ExpressionTree: An instance of the expression tree representing parameter dependencies.
        """
        tree = ExpressionTree(self.get_params())
        return tree
    
    def evaluate_tree_from_sm_params(self, tree : ExpressionTree) -> ExpressionTree:
        """
        Evaluates the expression tree using Standard Model parameters as inputs.
        
        Args:
            tree (ExpressionTree): The parameter dependency tree.
        
        Returns:
            ExpressionTree: The evaluated expression tree.
        """
        tree.evaluate_from_leaves([x["name"] for x in self.get_sm_params()])
    
        return tree
    
    def get_sm_param_tree_evaluated(self) -> ExpressionTree:
        """
        Constructs and evaluates an expression tree using only Standard Model parameters.
        
        Returns:
            ExpressionTree: The evaluated expression tree with SM parameters.
        """
        tree = self.get_param_tree()
        sm_tree = tree.get_subgraph_from_leaves([x["name"] for x in self.get_sm_params()])
        tree = self.evaluate_tree_from_sm_params(sm_tree)
        return sm_tree
    
    def get_param_with_sm_evaluation(self) -> List[Dict[str, Any]]:
        """
        Get all the parameters using only Standard Model parameters for calculation.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing all parameters (with SM evaluation).
        """
        tree = self.get_param_tree()
        tree = self.evaluate_tree_from_sm_params(tree)
        dot = tree.visualize()
        dot.render("eheh.png", format="png", view=False)
        return tree.convert_tree_to_list()