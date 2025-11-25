# tests/unit/utils/test_multiset_unit.py
import pytest

# ⚠️ ADAPTE ICI l'import vers l'endroit où vit ta classe
from SetAnubis.core.Common.MultiSet import MultiSet


def test_init_empty_and_from_iterable():
    m0 = MultiSet()
    assert len(m0) == 0
    m1 = MultiSet([1, 2, 2, 3])
    assert len(m1) == 4
    assert 2 in m1 and 4 not in m1


def test_add_remove_contains_len_iter():
    m = MultiSet([1])
    m.add(2)
    m.add(2)
    assert len(m) == 3
    assert 2 in m
    # itérable
    assert list(iter(m)) == [1, 2, 2]
    # remove enlève une seule occurrence
    m.remove(2)
    assert list(iter(m)) == [1, 2]
    # remove inexistant -> ValueError de list.remove
    with pytest.raises(ValueError):
        m.remove(42)


def test_count():
    m = MultiSet(["a", "b", "a", "a"])
    assert m.count("a") == 3
    assert m.count("b") == 1
    assert m.count("c") == 0


def test_equality_order_independent_and_multiplicity_sensitive():
    a = MultiSet([1, 1, 2])
    b = MultiSet([1, 2, 1])
    c = MultiSet([1, 2])
    assert a == b
    assert a != c


def test_union_intersection_difference():
    m1 = MultiSet([1, 1, 2, 3])
    m2 = MultiSet([1, 2, 2, 4])

    # union : concaténation des multisets
    u = m1.union(m2)
    assert u == MultiSet([1, 1, 2, 3, 1, 2, 2, 4])

    # intersection : min des multiplicités (par logique)
    inter = m1.intersection(m2)
    assert inter == MultiSet([1, 2])  # 1 min(2,1)=1 fois ; 2 min(1,2)=1 fois

    # difference : m1 \ m2 -> retire autant d'occurrences que présentes dans m2
    diff = m1.difference(m2)
    # m1 [1,1,2,3] - [1,2,2,4] = retire un '1' et un '2' -> reste [1,3]
    assert diff == MultiSet([1, 3])

    # autre cas : m1 - [1,1,1] -> ne retire que 2 occurrences existantes
    diff2 = MultiSet([1, 1, 2]).difference(MultiSet([1, 1, 1]))
    assert diff2 == MultiSet([2])


def test_repr_contains_items_and_current_name():
    m = MultiSet([1, 2])
    # Le __repr__ actuel renvoie "MultiBag([...])" (
