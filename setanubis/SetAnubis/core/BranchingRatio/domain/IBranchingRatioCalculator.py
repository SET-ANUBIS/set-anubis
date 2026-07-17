"""Branching-ratio calculator protocol."""

from typing import Protocol

from SetAnubis.core.Common.MultiSet import MultiSet


class IBranchingRatioCalculator(Protocol):
    """Contract implemented by branching-ratio and width calculators."""

    def get(
        self,
        br_type: str,
        mother_particle: int,
        daughters_particles: MultiSet,
    ) -> float:
        """Return a branching ratio or width for one decay channel.

        Args:
            br_type: Quantity to return, such as ``"Total BR"``, ``"BR"`` or
                ``"Width"``.
            mother_particle: PDG identifier of the decaying particle.
            daughters_particles: Multiset of daughter-particle PDG identifiers.

        Returns:
            The calculated branching ratio or width.
        """
        ...
