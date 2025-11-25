import math
import pytest

from SetAnubis.core.DataBase.domain.UFOTree import ExpressionTree, Node

def make_params():
    return [
        {"name": "a", "value": 2.0},
        {"name": "b", "value": 3.0},
        {"name": "x", "value": 7.0}, 
        {"name": "c", "expression": "a + b"},
        {"name": "d", "expression": "sqrt(c) + cmath.cos(a) + complex(0,1)*b"},
        {"name": "e", "expression": "2*c"},
        {"name": "f", "expression": "e + a"},
    ]

def test_build_tree_and_dependencies():
    tree = ExpressionTree(make_params())
    assert set(tree.nodes.keys()) == {"a","b","x","c","d","e","f"}
    assert sorted(dep.name for dep in tree.nodes["c"].dependencies) == ["a","b"]
    assert sorted(dep.name for dep in tree.nodes["e"].dependencies) == ["c"]
    assert sorted(dep.name for dep in tree.nodes["f"].dependencies) == ["a","e"]

def test_clean_expression_replaces_cmath_and_I():
    tree = ExpressionTree(make_params())
    expr = tree.nodes["d"].expression
    assert "cos(" in expr and "cmath.cos" not in expr
    assert "I*" in expr

def test_evaluate_partial_on_all_nodes():
    tree = ExpressionTree(make_params())
    tree.evaluate_partial(list(tree.nodes.keys()))
    c = tree.nodes["c"].value
    d = tree.nodes["d"].value
    e = tree.nodes["e"].value
    f = tree.nodes["f"].value
    assert c == complex(5.0, 0.0)
    expected_real = math.sqrt(5.0) + math.cos(2.0)
    assert d.real == pytest.approx(expected_real, rel=1e-12)
    assert d.imag == pytest.approx(3.0, rel=1e-12)
    assert e == complex(10.0, 0.0)
    assert f == complex(12.0, 0.0)

def test_copy_is_independent():
    tree = ExpressionTree(make_params())
    tree2 = tree.copy()
    tree2.set_leaf_value("a", 10.0)
    tree2.evaluate_partial(list(tree2.nodes.keys()))
    tree.evaluate_partial(list(tree.nodes.keys()))
    assert tree.nodes["c"].value == complex(5.0)
    assert tree2.nodes["c"].value == complex(13.0)

def test_convert_tree_to_list_and_rebuild():
    tree = ExpressionTree(make_params())
    params_list = tree.convert_tree_to_list()
    some = {p["name"]: p for p in params_list}
    assert "a" in some and "c" in some
    assert "value" in some["a"] and "expression" not in some["a"]
    assert "expression" in some["c"]

    rebuilt = ExpressionTree(params_list)
    rebuilt.evaluate_partial(list(rebuilt.nodes.keys()))
    assert rebuilt.nodes["f"].value == complex(12.0)

def test_set_leaf_value_success_and_errors():
    tree = ExpressionTree(make_params())
    tree.set_leaf_value("a", 4.5)
    assert tree.nodes["a"].value == 4.5
    with pytest.raises(ValueError):
        tree.set_leaf_value("c", 1.23)
    with pytest.raises(KeyError):
        tree.set_leaf_value("nope", 1.0)

def test_get_remaining_leaves():
    tree = ExpressionTree(make_params())
    remaining = set(tree.get_remaining_leaves(used_leaves=["a"]))
    assert remaining == {"b", "x"}

def test_evaluate_from_leaves_partial_and_full():
    tree = ExpressionTree(make_params())

    tree.set_leaf_value("a", 10.0)
    tree.evaluate_from_leaves(["a"])
    assert tree.nodes["c"].expression is not None
    assert "10.0" in tree.nodes["c"].expression and "b" in tree.nodes["c"].expression
    assert tree.nodes["c"].value is None

    tree.evaluate_from_leaves(["a", "b"])
    assert tree.nodes["c"].value == complex(13.0)
    assert tree.nodes["c"].expression is None
    assert tree.nodes["e"].value == complex(26.0)
    assert tree.nodes["e"].expression is None
    assert tree.nodes["f"].value == complex(36.0)
    assert tree.nodes["f"].expression is None

def test_get_subgraph_from_leaves_excludes_nodes_with_external_deps():
    params = [
        {"name": "a", "value": 2.0},
        {"name": "b", "value": 3.0},
        {"name": "z", "value": 0.5},
        {"name": "c", "expression": "a + b"},
        {"name": "d", "expression": "sqrt(c) + z"},
    ]
    tree = ExpressionTree(params)
    sub = tree.get_subgraph_from_leaves(["a", "b"])
    assert set(sub.nodes.keys()) == {"a", "b", "c"}

import re

def test_visualize_hides_orphan_leaf():
    tree = ExpressionTree(make_params())
    dot_all = tree.visualize(hide_orphan_leaves=False)
    dot_hide = tree.visualize(hide_orphan_leaves=True)

    assert re.search(r'^\s*x\s*\[', dot_all.source, re.M)
    assert not re.search(r'^\s*x\s*\[', dot_hide.source, re.M)


def test_get_value_returns_node_or_zero():
    tree = ExpressionTree(make_params())
    assert isinstance(tree.get_value("a"), Node)
    assert tree.get_value("does_not_exist") == 0
