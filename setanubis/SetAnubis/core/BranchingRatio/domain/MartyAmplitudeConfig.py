"""Configuration helpers for mediator-resolved MARTY amplitudes.

The public MARTY interface may split one physical process into diagram families,
for example a charged-current W contribution and a neutral-current Z
contribution.  Each family can use the fermion order that is natural for its
current structure.  SET-ANUBIS then keeps the families as distinct MARTY
``Amplitude`` objects and includes all pairwise cross terms when constructing
the squared matrix element.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from collections.abc import Mapping, Sequence
from typing import TypeAlias


MediatorKey: TypeAlias = str | tuple[str, ...]
MediatorFermionOrders: TypeAlias = Mapping[MediatorKey, Sequence[int] | None]


@dataclass(frozen=True)
class MartyAmplitudeComponent:
    """One non-overlapping mediator family and its fermion-order convention."""

    mediators: tuple[str, ...]
    fermion_order: tuple[int, ...] | None = None

    @property
    def label(self) -> str:
        """Human-readable deterministic component label."""
        return "+".join(self.mediators)


def _normalize_mediators(key: MediatorKey) -> tuple[str, ...]:
    if isinstance(key, str):
        values = (key,)
    elif isinstance(key, tuple):
        values = key
    else:
        raise TypeError(
            "mediator_fermion_orders keys must be mediator names (str) or "
            "tuples of mediator names"
        )

    mediators = tuple(str(value).strip() for value in values)
    if not mediators or any(not value for value in mediators):
        raise ValueError("Mediator names must be non-empty strings")
    if len(set(mediators)) != len(mediators):
        raise ValueError(f"Duplicate mediator in component {mediators!r}")
    return tuple(sorted(mediators))


def _normalize_order(order: Sequence[int] | None) -> tuple[int, ...] | None:
    if order is None:
        return None
    if isinstance(order, (str, bytes)):
        raise TypeError("fermion_order must be a sequence of integer indices")
    values = tuple(int(value) for value in order)
    if not values:
        raise ValueError("fermion_order cannot be empty; use None for MARTY default")
    if any(value < 0 for value in values):
        raise ValueError("fermion_order indices must be non-negative")
    if len(set(values)) != len(values):
        raise ValueError(f"fermion_order must not repeat indices: {values!r}")
    expected = tuple(range(len(values)))
    if tuple(sorted(values)) != expected:
        raise ValueError(
            "fermion_order must be a permutation of 0..N-1; "
            f"got {values!r}"
        )
    return values


def normalize_mediator_fermion_orders(
    value: MediatorFermionOrders | None,
) -> tuple[MartyAmplitudeComponent, ...]:
    """Normalize the public mediator -> fermion-order mapping.

    ``None`` (the default) keeps the historical SET-ANUBIS behaviour: one
    MARTY amplitude containing every diagram and MARTY's automatic fermion
    order.  A tuple key groups aliases/partners into a single diagram family;
    a diagram is retained when *any* mediator in that tuple is present.

    Components must be non-overlapping at the diagram level.  This is natural
    for tree-level W/Z decomposition; overlapping families would double count
    a diagram and are therefore rejected when the same mediator name appears
    in more than one component.
    """
    if value is None:
        return ()
    if not isinstance(value, Mapping):
        raise TypeError("mediator_fermion_orders must be a mapping or None")
    if not value:
        raise ValueError("mediator_fermion_orders cannot be empty; use None instead")

    components: list[MartyAmplitudeComponent] = []
    seen: set[str] = set()
    for key, order in value.items():
        mediators = _normalize_mediators(key)
        overlap = seen.intersection(mediators)
        if overlap:
            raise ValueError(
                "A mediator may belong to only one amplitude component; "
                f"repeated: {sorted(overlap)!r}"
            )
        seen.update(mediators)
        components.append(
            MartyAmplitudeComponent(
                mediators=mediators,
                fermion_order=_normalize_order(order),
            )
        )

    # Equivalent dictionaries should generate the same source/cache key even
    # if their insertion order differs.
    components.sort(key=lambda component: component.mediators)
    return tuple(components)


def amplitude_config_suffix(
    components: tuple[MartyAmplitudeComponent, ...],
) -> str:
    """Return a short stable cache suffix for a non-default amplitude split."""
    if not components:
        return ""

    payload = [
        {
            "mediators": list(component.mediators),
            "fermion_order": (
                list(component.fermion_order)
                if component.fermion_order is not None
                else None
            ),
        }
        for component in components
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = sha256(encoded.encode("utf-8")).hexdigest()[:10]
    # This suffix is reused by MARTY as part of generated C/C++ identifiers
    # (namespaces, include guards and library symbols), not only as a
    # filesystem name. MARTY also normalizes generated namespaces to
    # lowercase, so make the cache suffix lowercase and identifier-safe from
    # the start. The digest still distinguishes labels that sanitize to the
    # same visible fragment.
    labels = "_".join(component.label for component in components).lower()
    labels = re.sub(r"[^a-z0-9_]+", "_", labels).strip("_")[:48]
    if not labels:
        labels = "components"
    return f"__mfo_{labels}_{digest}"
