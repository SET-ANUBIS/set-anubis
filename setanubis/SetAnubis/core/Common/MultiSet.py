from typing import TypeVar, Generic, Iterable, Iterator
from collections import Counter

T = TypeVar('T')

class MultiSet(Generic[T]):
    def __init__(self, iterable: Iterable[T] = None):
        self.items: list[T] = list(iterable) if iterable else []

    def __eq__(self, other):
        if not isinstance(other, MultiSet):
            return NotImplemented
        return Counter(self.items) == Counter(other.items)

    def __hash__(self):

        return hash(frozenset(Counter(self.items).items()))
    
    def __repr__(self):
        return f"MultiSet({self.items})"

    def add(self, item):
        self.items.append(item)

    def remove(self, item):
        self.items.remove(item)

    def __contains__(self, item) -> bool:
        return item in self.items

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[T]:
        return iter(self.items)
    
    def count(self, item: T) -> int:
        """Renvoie le nombre d'occurrences de l'élément."""
        return self.items.count(item)


    def union(self, other: 'MultiSet[T]') -> 'MultiSet[T]':
        return MultiSet(self.items + other.items)

    def intersection(self, other: 'MultiSet[T]') -> 'MultiSet[T]':
        result = []
        copy_other = list(other.items)
        for item in self.items:
            if item in copy_other:
                result.append(item)
                copy_other.remove(item)
        return MultiSet(result)

    def difference(self, other: 'MultiSet[T]') -> 'MultiSet[T]':
        result = list(self.items)
        for item in other.items:
            if item in result:
                result.remove(item)
        return MultiSet(result)
    
    
    
if __name__ == "__main__":
    a = MultiSet([11, -12])
    b = MultiSet([-12, 11])

    print(a == b)  # True (avec ton __eq__ actuel)
    d = {a: "ok"}
    print(d[b])    # KeyError si __hash__ ne suit pas la même logique