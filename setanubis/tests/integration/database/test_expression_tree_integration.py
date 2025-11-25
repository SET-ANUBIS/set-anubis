import math
import pytest

from SetAnubis.core.DataBase.domain.UFOTree import ExpressionTree

def make_big_params():
    return [
        {"name": "a", "value": 1.5},
        {"name": "b", "value": 2.0},
        {"name": "u", "value": 0.7}, 
        {"name": "c", "expression": "a + 2*b"},
        {"name": "d", "expression": "c**2 + sin(a)"},
        {"name": "e", "expression": "sqrt(d) + cos(b)"},
        {"name": "g", "expression": "e + a*b"},
    ]

def test_manager_style_full_evaluation_then_rebuild_and_copy():
    tree = ExpressionTree(make_big_params())
    tree.evaluate_partial(list(tree.nodes.keys()))
    v1 = complex(tree.nodes["g"].value)

    rebuilt = tree.rebuild_tree()
    assert rebuilt.nodes["g"].expression is None

    copy_tree = rebuilt.copy()
    copy_tree.set_leaf_value("a", 10.0)
    copy_tree.evaluate_partial(list(copy_tree.nodes.keys()))
    v2 = complex(copy_tree.nodes["g"].value)

    assert v1 == v2

def test_subgraph_then_eval_matches_full_result_for_its_scope():
    params = [
        {"name": "a", "value": 2.0},
        {"name": "b", "value": 1.0},
        {"name": "c", "expression": "a + 2*b"},
        {"name": "d", "expression": "c**2 + sin(a)"},
        {"name": "e", "expression": "sqrt(d) + cos(b)"},
        {"name": "g", "expression": "e + a*b"},
    ]
    full = ExpressionTree(params)
    full.evaluate_partial(list(full.nodes.keys()))
    d_full = complex(full.nodes["d"].value)

    sub = full.get_subgraph_from_leaves(["a","b"])
    assert set(sub.nodes.keys()) == {"a","b","c","d","e","g"}

    sub.evaluate_partial(list(sub.nodes.keys()))
    assert complex(sub.nodes["d"].value) == pytest.approx(d_full, rel=1e-12)


def test_graphviz_source_is_well_formed_without_rendering():
    tree = ExpressionTree(make_big_params())
    dot = tree.visualize(hide_orphan_leaves=False)
    src = dot.source
    assert "digraph" in src and "->" in src
    for n in ["a","b","c","d","e","g"]:
        assert n in src
