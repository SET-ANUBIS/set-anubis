import os
from SetAnubis.core.DataBase.domain.UFOManager import UFOManager
import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
from SetAnubis.core.Common.MultiSet import MultiSet

class DecayUFOManager:
    def __init__(self, ufo_path =""):
        self.ufo_path = ufo_path
        self.ufo_manager = UFOManager(self.ufo_path )

        self.decay_from_new_particles = self.ufo_manager.get_decays_from_new_particles()
        self.decay_to_new_particles = self.ufo_manager.get_decays_to_new_particles()
        self.decay_from_new_particles = [list(self.decay_from_new_particles[x].keys()) for x in self.decay_from_new_particles.keys()]
        self.decay_to_new_particles = [list(self.decay_to_new_particles[x].keys()) for x in self.decay_to_new_particles.keys()]
        self.new_particles = self.ufo_manager.get_new_particles()
        self.decays = self.ufo_manager.get_decays()
        
        self.func = dict()
        self.params = dict()
        
    def evaluate_with_sm(self):
        sm_tree = self.ufo_manager.get_sm_param_tree_evaluated()

        sm_params = {x.name:x.value for x in sm_tree.nodes.values()}

        for part, decays in self.decays.items():
            for pair, decay in decays.items():
                sympy_expr = sp.sympify(decay, locals={k: sp.Symbol(k) for k in sm_params.keys()})

                substituted_expr = sympy_expr.subs({k: v for k, v in sm_params.items() if v is not None})

                simplified_expr = sp.simplify(substituted_expr)

                simplified_expr_str = str(simplified_expr)
                self.decays[part][pair] = simplified_expr_str
                


    def __generate_function_from_expression(self, expression_str: str):
        """
        Transforme une expression mathématique en une fonction Python prenant un dictionnaire comme paramètre.

        Args:
            expression_str (str): L'expression mathématique sous forme de chaîne.

        Returns:
            Callable: Une fonction Python prenant un dictionnaire et retournant la valeur de l'expression.
        """
        sympy_expr = sp.sympify(expression_str)

        variables = list(sympy_expr.free_symbols)

        def func(params_dict):
            subs_dict = {var: params_dict.get(str(var), 0) for var in variables}
            return float(sympy_expr.evalf(subs=subs_dict))

        return func, [str(var) for var in variables]

    def create_func_caches(self):
        self.func = dict()
        for part, decays in self.decays.items():
            self.func[part] = dict()
            self.params[part] = dict()
            for pair, decay in decays.items():
                func, param_list = self.__generate_function_from_expression(decay)
                self.func[part][pair] = func
                self.params[part][pair] = param_list

    def evaluate(self, mother : str, daughters : MultiSet, params):
        return self.func[mother][daughters](params)
    
    def get_function(self, mother : int, daughters : MultiSet):
        return self.func[mother][daughters]
    
    def get_caches(self):
        return self.func, self.params


