"""Evaluate and cache decay expressions extracted from a trusted UFO model."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Tuple

import sympy as sp

from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.DataBase.domain.UFOManager import UFOManager


_SYMPY_UFO_FUNCTIONS: Dict[str, Any] = {
    "complexconjugate": sp.conjugate,
    "re": sp.re,
    "im": sp.im,
    "csc": sp.csc,
    "sec": sp.sec,
    "acsc": sp.acsc,
    "asec": sp.asec,
    "cot": sp.cot,
}


class DecayUFOManager:
    """Prepare numerical callables for decay expressions stored in a UFO model."""

    def __init__(self, ufo_path: str = "") -> None:
        """Load decay expressions and particle metadata from ``ufo_path``."""
        self.ufo_path = ufo_path
        self.ufo_manager = UFOManager(self.ufo_path)

        from_new = self.ufo_manager.get_decays_from_new_particles()
        to_new = self.ufo_manager.get_decays_to_new_particles()
        self.decay_from_new_particles = [list(channels) for channels in from_new.values()]
        self.decay_to_new_particles = [list(channels) for channels in to_new.values()]
        self.new_particles = self.ufo_manager.get_new_particles()
        self.decays = self.ufo_manager.get_decays()

        self.func: Dict[int, Dict[MultiSet[int], Callable[[Dict[str, Any]], float]]] = {}
        self.params: Dict[int, Dict[MultiSet[int], list[str]]] = {}

    @staticmethod
    def _parse_expression(expression: str, symbols: Iterable[str] = ()) -> sp.Expr:
        """Parse a UFO expression with the standard UFO helper functions."""
        local_symbols = {name: sp.Symbol(name) for name in symbols}
        return sp.sympify(expression, locals={**_SYMPY_UFO_FUNCTIONS, **local_symbols})

    def evaluate_with_sm(self) -> None:
        """Substitute evaluated Standard Model parameters into every decay expression."""
        sm_tree = self.ufo_manager.get_sm_param_tree_evaluated()
        sm_params = {node.name: node.value for node in sm_tree.nodes.values()}

        for part, decays in self.decays.items():
            for pair, decay in decays.items():
                expression = self._parse_expression(decay, sm_params)
                substituted = expression.subs(
                    {name: value for name, value in sm_params.items() if value is not None}
                )
                self.decays[part][pair] = str(sp.simplify(substituted))

    @classmethod
    def _generate_function_from_expression(
        cls, expression: str
    ) -> Tuple[Callable[[Dict[str, Any]], float], list[str]]:
        """Convert an expression into a callable accepting a parameter dictionary."""
        sympy_expr = cls._parse_expression(expression)
        variables = sorted(sympy_expr.free_symbols, key=lambda symbol: str(symbol))

        def func(params_dict: Dict[str, Any]) -> float:
            missing = [str(variable) for variable in variables if str(variable) not in params_dict]
            if missing:
                raise KeyError(f"Missing UFO decay parameters: {missing}")
            substitutions = {variable: params_dict[str(variable)] for variable in variables}
            value = complex(sympy_expr.evalf(subs=substitutions))
            if abs(value.imag) > 1e-12:
                raise ValueError(
                    "UFO decay expression evaluated to a complex value: "
                    f"{value}"
                )
            return float(value.real)

        return func, [str(variable) for variable in variables]

    def create_func_caches(self) -> None:
        """Create callable and parameter-name caches for every decay channel."""
        self.func = {}
        self.params = {}
        for part, decays in self.decays.items():
            self.func[part] = {}
            self.params[part] = {}
            for pair, decay in decays.items():
                function, parameter_list = self._generate_function_from_expression(decay)
                self.func[part][pair] = function
                self.params[part][pair] = parameter_list

    def evaluate(
        self,
        mother: int,
        daughters: MultiSet[int],
        params: Dict[str, Any],
    ) -> float:
        """Evaluate a previously cached decay channel."""
        return self.func[mother][daughters](params)

    def get_function(
        self, mother: int, daughters: MultiSet[int]
    ) -> Callable[[Dict[str, Any]], float]:
        """Return the cached function for one decay channel."""
        return self.func[mother][daughters]

    def get_caches(self) -> tuple[dict, dict]:
        """Return the function and parameter-name caches."""
        return self.func, self.params
