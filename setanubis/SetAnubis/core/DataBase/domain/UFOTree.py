import sympy as sp
import graphviz
from typing import Dict, List, Any, Optional, Set
import copy

class Node:
    """
    Represents a node in the expression tree.
    
    Attributes:
        name (str): The name of the node.
        value (Optional[float]): The numerical value of the node if it is a constant.
        expression (Optional[str]): The mathematical expression of the node if it depends on others.
        dependencies (List[Node]): The list of dependent nodes.
        lha_block (Optional[str]): The LHA block associated with the node.
        lha_code (Optional[List[int]]): The LHA code of the node.
    """
    def __init__(self, name: str, value: Optional[float] = None, expression: Optional[str] = None,
                 lha_block: Optional[str] = None, lha_code: Optional[List[int]] = None):
        """Initialize a node.

        Args:
            name: Unique node name.
            value: Numeric value if the node is a constant.
            expression: Symbolic expression if the node is not a constant.
            lha_block: Associated LHA block.
            lha_code: Associated LHA/PDG code(s).

        Note:
            The `dependencies` attribute is initialized empty and is populated by
            :meth:`ExpressionTree.build_tree`.
        """
        self.name = name
        self.value = value
        self.expression = expression
        self.dependencies = []
        self.lha_block = lha_block
        self.lha_code = lha_code

    def __repr__(self):
        """Return a concise, human-readable representation.

        Returns:
            str: Summary including name, value, expression, and dependency count.
        """
        return f"Node({self.name}, value={self.value}, expr={self.expression}, deps={len(self.dependencies)})"

class ExpressionTree:
    """Manages a dependency graph and supports partial evaluations.

    The tree is built from a list of parameters describing numeric leaves or
    symbolic expressions. Dependencies are inferred using SymPy.

    Attributes:
        nodes (Dict[str, Node]): Mapping of node names to nodes.
    """
    def __init__(self, params: List[Dict[str, Any]]):
        """Create an expression tree and build its dependencies.

        Args:
            params: List of dictionaries describing each node with keys:
                - "name" (str, required)
                - "value" (number) or "expression" (str)
                - "block" (str, optional)
                - "pdgcode" (List[int], optional)

        Side Effects:
            Populates `self.nodes` and calls :meth:`build_tree`.
        """
        self.nodes = {}
        self.build_tree(params)

    def build_tree(self, params: List[Dict[str, Any]]):
        """Build the dependency graph from the given parameters.

        Args:
            params: Input parameters (see `__init__`).

        Side Effects:
            - Creates `Node` objects in `self.nodes`.
            - Normalizes expressions via :meth:`clean_expression`.
            - Infers and fills each node’s `dependencies` using SymPy.

        Raises:
            sympy.SympifyError: If an expression cannot be parsed.
        """
        for param in params:
            name = param["name"]
            value = param.get("value", None)
            lha_block = param.get("block", None)
            lha_code = param.get("pdgcode", None)

            if isinstance(value, (int, float, complex)):
                self.nodes[name] = Node(name, value=value, lha_block=lha_block, lha_code=lha_code)
            else:
                if value is None:
                    value = param["expression"]
                cleaned_expr = self.clean_expression(value) 
                self.nodes[name] = Node(name, expression=cleaned_expr, lha_block=lha_block, lha_code=lha_code)

        for node in self.nodes.values():
            if node.expression:
                sympy_expr = sp.sympify(node.expression, locals={k: sp.Symbol(k) for k in self.nodes.keys()})

                for var in sympy_expr.free_symbols:
                    var_name = str(var)
                    if var_name in self.nodes:
                        node.dependencies.append(self.nodes[var_name]) 

    def copy(self) -> "ExpressionTree":
        """Return a deep copy of the expression tree.

        Returns:
            ExpressionTree: Independent clone with identical structure and values.
        """
        copied_params = self.convert_tree_to_list()
        return ExpressionTree(copy.deepcopy(copied_params))

    def convert_tree_to_list(self) -> List[Dict[str, Any]]:
        """Serialize the tree (dict of `Node`) into a list of dictionaries.

        Returns:
            List[Dict[str, Any]]: Serializable node descriptors. Keys
            with `None` values are omitted.
        """
        params = []

        for name, node in self.nodes.items():
            node_dict = {
                "name": name,
                "value": node.value,
                "block": node.lha_block,
                "pdgcode": node.lha_code,
                "expression": node.expression
            }

            node_dict = {k: v for k, v in node_dict.items() if v is not None}
            params.append(node_dict)

        return params
    
    def clean_expression(self, expression_str: str) -> str:
        """Replace `cmath` functions with their SymPy equivalents.

        Args:
            expression_str: Mathematical expression as a string.

        Returns:
            str: Cleaned expression (e.g., `cmath.sqrt` → `sqrt`, `complex(0,1)` → `I`).
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

    def evaluate(self, node: Node, evaluated_nodes: Set[str]) -> float:
        """Recursively evaluate a node while respecting dependencies.

        Args:
            node: The node to evaluate.
            evaluated_nodes: Set of names already evaluated (prevents redundant work).

        Returns:
            complex: The computed numeric value. The implementation casts results
            to `complex` even for real values.

        Raises:
            sympy.SympifyError: If the expression cannot be parsed.
            Exception: If a required dependency cannot be evaluated.

        Note:
            Although the type annotation is `float`, the function returns a `complex`
            value in practice.
        """
        if node.value is not None:
            return node.value

        if node.name in evaluated_nodes:
            return self.nodes[node.name].value

        expression_str = self.clean_expression(node.expression)
        sympy_expr = sp.sympify(expression_str, locals={k: v.value if v.value is not None else sp.Symbol(k) for k, v in self.nodes.items()})

        values_dict = {dep.name: self.evaluate(dep, evaluated_nodes) for dep in node.dependencies}
        if isinstance(sympy_expr, (int, float, complex)):
            node.value = complex(sympy_expr)
        else:
            node.value = complex(sympy_expr.evalf(subs=values_dict))
        evaluated_nodes.add(node.name)
        return node.value

    def evaluate_partial(self, leaf_names: List[str]):
        """Partially evaluate the tree by resolving only selected leaves/subgraphs.

        Args:
            leaf_names: Names of leaves to evaluate (including their transitive dependencies).
        """
        evaluated_nodes = set()
        for name in leaf_names:
            if name in self.nodes:
                self.evaluate(self.nodes[name], evaluated_nodes)

    def rebuild_tree(self) -> "ExpressionTree":
        """Rebuild a simplified tree where evaluated nodes become leaves.

        Returns:
            ExpressionTree: New tree in which evaluated nodes carry a `value`,
            and others retain their `expression`.
        """
        new_params = []
        for node in self.nodes.values():
            if node.value is not None:
                new_params.append({"name": node.name, "value": node.value, "block": node.lha_block, "pdgcode": node.lha_code})
            else:
                new_params.append({"name": node.name, "value": node.expression, "block": node.lha_block, "pdgcode": node.lha_code})
        
        return ExpressionTree(new_params)

    def visualize(self, hide_orphan_leaves: bool = False):
        """Generate a Graphviz visualization of the expression tree.

        Args:
            hide_orphan_leaves: If True, hide orphan leaves (those not used as
                dependencies by any node).

        Returns:
            graphviz.Digraph: Directed, labeled graph (name plus value or expression).
        """
        dot = graphviz.Digraph(comment="Expression Tree")

        dependent_nodes = set()
        for node in self.nodes.values():
            for dep in node.dependencies:
                dependent_nodes.add(dep.name)

        for node in self.nodes.values():
            was_expression = node.expression is not None  

            if hide_orphan_leaves and node.value is not None and not was_expression and node.name not in dependent_nodes:
                continue 

            label = f"{node.name}\n{node.value if node.value is not None else node.expression}"
            dot.node(node.name, label=label)

        for node in self.nodes.values():
            for dep in node.dependencies:
                dot.edge(dep.name, node.name)

        return dot

    def evaluate_from_leaves(self, leaf_names: List[str]):
        """Substitute specified leaves and propagate updates through dependent nodes.

        The provided leaf values are substituted into the expressions of nodes that
        depend on them. Nodes that become fully numeric are evaluated and converted
        to leaves (their `expression` is set to `None`).

        Args:
            leaf_names: Names of leaves to substitute.

        Raises:
            sympy.SympifyError: If an expression cannot be parsed.
        """
        evaluated_nodes = set()

        for name in leaf_names:
            if name in self.nodes:
                self.evaluate(self.nodes[name], evaluated_nodes)

        affected_nodes = set()
        queue = list(leaf_names)

        while queue:
            current = queue.pop(0)
            for node in self.nodes.values():
                if len(node.dependencies) == 0:
                    continue
                if node.expression and any(dep.name == current for dep in node.dependencies):
                    if node.name not in affected_nodes:
                        affected_nodes.add(node.name)
                        queue.append(node.name)

        to_check = affected_nodes

        while to_check:
            updated = False
            new_to_check = set()
            for node in self.nodes.values():
                if node.name in to_check and node.expression:
                    values_dict = {dep.name: dep.value for dep in node.dependencies if dep.name in affected_nodes.union(set(leaf_names))}
                    values_dict = {x:y for x,y in values_dict.items() if y is not None}
                    sympy_expr = sp.sympify(node.expression, locals={k: sp.Symbol(k) for k in self.nodes.keys()})
                    new_expr = sympy_expr.subs(values_dict)
                    if new_expr.is_number:
                        node.value = complex(new_expr.evalf())
                        node.expression = None
                        updated = True 
                        new_to_check.update(dep.name for dep in self.nodes.values() if node in dep.dependencies)
                    else:
                        node.expression = str(new_expr)
                        updated = True

 
            if updated:
                to_check = new_to_check
            else:
                break


    def get_remaining_leaves(self, used_leaves: List[str]) -> List[str]:
        """Return the set of leaves not present in `used_leaves`.

        Args:
            used_leaves: Names of leaves already used.

        Returns:
            List[str]: Names of available leaves (nodes without an `expression`).
        """
        all_leaves = [name for name, node in self.nodes.items() if not node.expression]
        remaining_leaves = [leaf for leaf in all_leaves if leaf not in used_leaves]
        return remaining_leaves


    def set_leaf_value(self, leaf_name: str, value: float):
        """Assign a new value to an existing leaf.

        Args:
            leaf_name: Name of the leaf to update.
            value: New numeric value.

        Raises:
            KeyError: If the node does not exist.
            ValueError: If the node is not a leaf (it has an `expression`).
        """
        if leaf_name in self.nodes:
            node = self.nodes[leaf_name]
            if not node.expression:
                node.value = value
            else:
                raise ValueError(f"Le nœud {leaf_name} n'est pas une feuille !")
        else:
            raise KeyError(f"Le nœud {leaf_name} n'existe pas dans l'arbre.")

    def get_subgraph_from_leaves(self, leaf_names: List[str]) -> "ExpressionTree":
        """Build a subgraph containing only given leaves and nodes derived solely from them.

        A node is included if *all* its dependencies are already included, starting
        from the specified leaves and moving upward.

        Args:
            leaf_names: Names of the base leaves to keep.

        Returns:
            ExpressionTree: New tree restricted to the relevant nodes.
        """
        valid_nodes = set(leaf_names)
        queue = list(leaf_names)

        while queue:
            current = queue.pop(0)

            for node in self.nodes.values():
                if node.expression and node.name not in valid_nodes:
                    if all(dep.name in valid_nodes for dep in node.dependencies):
                        valid_nodes.add(node.name)
                        queue.append(node.name)

        subgraph_params = [
            {
                "name": node.name,
                "value": node.value if node.value is not None else node.expression,
                "block": node.lha_block,
                "pdgcode": node.lha_code
            }
            for node in self.nodes.values() if node.name in valid_nodes
        ]

        return ExpressionTree(subgraph_params) 
    
    def get_value(self, name : str):
        """Return the entry corresponding to the given node name.

        Args:
            name: Target node name.

        Returns:
            Node | int: The `Node` object if it exists; otherwise `0`.

        Note:
            Despite the method name, the return value is the `Node` object (or `0`),
            not its numeric `value` attribute.
        """
        return self.nodes.get(name, 0)
    
    def add_leaf(self, name: str, value: Optional[float] = None,
        lha_block: Optional[str] = None,
        lha_code: Optional[List[int]] = None,
        overwrite: bool = False):
        """Ajoute (ou remplace) un nœud feuille.


        Args:
        name: Nom unique du nœud.
        value: Valeur numérique (peut être None pour une feuille "placeholder").
        lha_block: Bloc LHA optionnel.
        lha_code: Code(s) LHA/PDG optionnel(s).
        overwrite: Si False, lève une erreur si *name* existe déjà.
        """
        if name in self.nodes and not overwrite:
            return #TODO : for now no warning
            raise ValueError(f"Le nœud '{name}' existe déjà. Utilisez overwrite=True pour remplacer.")


        self.nodes[name] = Node(name, value=value, lha_block=lha_block, lha_code=lha_code)


        # Relier les dépendances des autres nœuds susceptibles de référencer ce nom
        self._relink_dependencies(only_for={name})


    def add_expression(self, name: str, expression: str,
        lha_block: Optional[str] = None,
        lha_code: Optional[List[int]] = None,
        overwrite: bool = False,
        create_missing: bool = False):
        """Ajoute (ou remplace) un nœud défini par une expression symbolique.


        Args:
        name: Nom du nœud à créer/remplacer.
        expression: Expression (str), p.ex. "2*a + sin(b)".
        lha_block: Bloc LHA optionnel.
        lha_code: Code(s) LHA/PDG optionnel(s).
        overwrite: Si False, lève une erreur si *name* existe déjà.
        create_missing: Si True, crée automatiquement des feuilles vides pour
        toute dépendance manquante.


        Raises:
        KeyError: Si des dépendances sont absentes et *create_missing* est False.
        ValueError: Si l'ajout introduit une dépendance cyclique.
        """
        if name in self.nodes and not overwrite:
            raise ValueError(f"Le nœud '{name}' existe déjà. Utilisez overwrite=True pour remplacer.")


        cleaned = self.clean_expression(expression)


        # Identifier les symboles libres de l'expression
        tmp_locals = {k: sp.Symbol(k) for k in self.nodes.keys() | {name}}
        sympy_expr = sp.sympify(cleaned, locals=tmp_locals)
        deps = {str(s) for s in sympy_expr.free_symbols if str(s) != name}


        # Créer les dépendances manquantes si demandé
        missing = [d for d in deps if d not in self.nodes]
        if missing:
            if create_missing:
                for d in missing:
                    # Feuille placeholder (value=None, expression=None)
                    self.nodes[d] = Node(d)
            else:
                raise KeyError(f"Dépendances absentes pour '{name}': {missing}")


        # Installer le nœud
        self.nodes[name] = Node(name, expression=cleaned, lha_block=lha_block, lha_code=lha_code)


        # (Re)lier toutes les dépendances pertinentes
        self._relink_dependencies()


        # Détecter un éventuel cycle et annuler si nécessaire
        if self._has_cycle():
        # rollback simple
            del self.nodes[name]
            self._relink_dependencies()
            raise ValueError(f"Ajout de '{name}' rejeté: dépendance cyclique détectée.")


    def add_nodes(self, params: List[Dict[str, Any]],
        overwrite: bool = False,
        create_missing: bool = False):
        """Ajout en lot de feuilles et/ou de nœuds d'expression (même format que le ctor).


        Chaque entrée suit le format:
        {"name": str, "value": number | str, "block": str?, "pdgcode": List[int]?}
        - Si *value* est numérique → feuille
        - Si *value* est une str ou si *expression* est fourni → nœud d'expression


        Args:
        params: Liste de descripteurs de nœuds.
        overwrite: Autoriser le remplacement si un nom existe déjà.
        create_missing: Créer automatiquement les dépendances manquantes.
        """
        # On ajoute d'abord tous les noms (sans relier), puis on relie à la fin.
        staged: Dict[str, Node] = {}


        for p in params:
            name = p["name"]
            lha_block = p.get("block")
            lha_code = p.get("pdgcode")


            if name in self.nodes and not overwrite:
                raise ValueError(f"Le nœud '{name}' existe déjà. Utilisez overwrite=True pour remplacer.")


            if "expression" in p:
                val = p["expression"]
            else:
                val = p.get("value", None)


            if isinstance(val, (int, float, complex)):
                staged[name] = Node(name, value=val, lha_block=lha_block, lha_code=lha_code)
            else:
                if val is None:
                    raise ValueError(f"Le nœud '{name}' n'a ni valeur numérique ni expression.")
                cleaned = self.clean_expression(str(val))
                staged[name] = Node(name, expression=cleaned, lha_block=lha_block, lha_code=lha_code)


        # Appliquer dans self.nodes
        for name, node in staged.items():
            self.nodes[name] = node


        # Créer les dépendances manquantes si voulu
        if create_missing:
            all_needed: Set[str] = set()
            for node in self.nodes.values():
                if node.expression:
                    expr = sp.sympify(node.expression, locals={k: sp.Symbol(k) for k in self.nodes.keys()})
                    all_needed |= {str(s) for s in expr.free_symbols}
            for d in sorted(all_needed):
                if d not in self.nodes:
                    self.nodes[d] = Node(d)


        # Relier & vérifier les cycles
        self._relink_dependencies()
        if self._has_cycle():
            raise ValueError("Ajout en lot rejeté: dépendance cyclique détectée.")


    # --------------------- Helpers internes ---------------------
    def _relink_dependencies(self, only_for: Optional[Set[str]] = None):
        """(Ré)calcule la liste des dépendances pour les nœuds d'expression.


        Args:
        only_for: Si fourni, ne recalculer que les nœuds dont l'expression
        mentionne l'un de ces noms (ou ces nœuds eux‑mêmes).
        """
        all_symbols = {k: sp.Symbol(k) for k in self.nodes.keys()}


        for node in self.nodes.values():
            # Nettoyage des feuilles
            if not node.expression:
                node.dependencies = []
                continue


            sympy_expr = sp.sympify(node.expression, locals=all_symbols)
            free = {str(s) for s in sympy_expr.free_symbols}


            if (only_for is None) or (node.name in only_for) or (free & only_for):
                node.dependencies = [self.nodes[n] for n in free if n in self.nodes]


    def _has_cycle(self) -> bool:
        """Détection de cycle par DFS couleurs (O(N+E))."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {name: WHITE for name in self.nodes}


        def visit(u: str) -> bool:
            if color[u] == GRAY:
                return True # back-edge → cycle
            if color[u] == BLACK:
                return False
            color[u] = GRAY
            for dep in self.nodes[u].dependencies:
                if visit(dep.name):
                    return True
            color[u] = BLACK
            return False


        for name in list(self.nodes.keys()):
            if color[name] == WHITE:
                if visit(name):
                    return True
        return False