# tests/integration/utils/test_multiset_integration.py
from collections import Counter

# ⚠️ ADAPTE ICI l'import vers l'endroit où vit ta classe
from SetAnubis.core.Common.MultiSet import MultiSet


def multiset_from_str(s: str) -> MultiSet[str]:
    return MultiSet(list(s))


def counter_to_list(c: Counter) -> list:
    # Transforme Counter en liste avec multiplicités
    out = []
    for k, n in c.items():
        out.extend([k] * n)
    return out


def test_multiset_letters_operations_match_counter_logic():
    a = "banana"    # b=1, a=3, n=2
    b = "bandana"   # b=1, a=3, n=2, d=1

    mA = multiset_from_str(a)
    mB = multiset_from_str(b)

    # Union (concat) → Counter(a)+Counter(b) n'est pas exactement une union multiset,
    # on compare via listes triées de concaténation
    u = mA.union(mB)
    assert sorted(list(u)) == sorted(list(a + b))

    # Intersection (min des comptes)
    inter = mA.intersection(mB)
    inter_expected = Counter(a) & Counter(b)   # min des multiplicités
    assert sorted(list(inter)) == sorted(counter_to_list(inter_expected))

    # Différence (soustraction tronquée à 0)
    diff = mB.difference(mA)  # lettres en plus dans b
    diff_expected = Counter(b) - Counter(a)
    assert sorted(list(diff)) == sorted(counter_to_list(diff_expected))

    # Symétrique : (A \ B) ∪ (B \ A)
    sym = mA.difference(mB).union(mB.difference(mA))
    sym_expected = (Counter(a) - Counter(b)) + (Counter(b) - Counter(a))
    assert sorted(list(sym)) == sorted(counter_to_list(sym_expected))
