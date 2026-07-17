from collections import Counter

from SetAnubis.core.Common.MultiSet import MultiSet


def multiset_from_str(s: str) -> MultiSet[str]:
    return MultiSet(list(s))


def counter_to_list(c: Counter) -> list:
    # Convert a Counter to a list while preserving multiplicities
    out = []
    for k, n in c.items():
        out.extend([k] * n)
    return out


def test_multiset_letters_operations_match_counter_logic():
    a = "banana"    # b=1, a=3, n=2
    b = "bandana"   # b=1, a=3, n=2, d=1

    mA = multiset_from_str(a)
    mB = multiset_from_str(b)

    # Union concatenates values; Counter(a) + Counter(b) models this behavior.
    u = mA.union(mB)
    assert sorted(list(u)) == sorted(list(a + b))

    # Intersection uses the minimum count
    inter = mA.intersection(mB)
    inter_expected = Counter(a) & Counter(b)   # minimum multiplicity
    assert sorted(list(inter)) == sorted(counter_to_list(inter_expected))

    diff = mB.difference(mA)  # letters present in b after subtracting a
    diff_expected = Counter(b) - Counter(a)
    assert sorted(list(diff)) == sorted(counter_to_list(diff_expected))

    # (A \ B) ∪ (B \ A)
    sym = mA.difference(mB).union(mB.difference(mA))
    sym_expected = (Counter(a) - Counter(b)) + (Counter(b) - Counter(a))
    assert sorted(list(sym)) == sorted(counter_to_list(sym_expected))
