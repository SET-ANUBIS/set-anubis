from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple
import pandas as pd

@dataclass(frozen=True)
class Range:
    """Closed numeric interval filter.

    Both bounds are inclusive when provided.

    Attributes:
        lo: Lower bound. No lower constraint is applied when ``None``.
        hi: Upper bound. No upper constraint is applied when ``None``.
    """
    lo: Optional[float] = None
    hi: Optional[float] = None

    def contains(self, x: pd.Series) -> pd.Series:
        """Return a boolean mask indicating whether values are in range.

        Args:
            x: Series of numeric values to test.

        Returns:
            A boolean series with the same index as ``x``.
        """
        ok = pd.Series(True, index=x.index)
        if self.lo is not None:
            ok &= x >= self.lo
        if self.hi is not None:
            ok &= x <= self.hi
        return ok

@dataclass(frozen=True)
class ParticleFilterSpec:
    """Filtering specification applied to an extracted particle table.

    The filter can constrain particle topology using mother/child PDG IDs and
    can also apply numeric ranges to kinematic columns.

    Attributes:
        mother_pid: Required mother PDG ID.
        child_pid: Required child PDG ID.
        E: Allowed energy range.
        pt: Allowed transverse momentum range.
        p: Allowed momentum magnitude range.
        px: Allowed x momentum component range.
        py: Allowed y momentum component range.
        pz: Allowed z momentum component range.
        eta: Allowed pseudorapidity range.
        phi: Allowed azimuthal angle range.
        theta: Allowed polar angle range.
        met: Allowed event MET range.
        max_rows: Maximum number of rows to keep after filtering. When the
            result is larger, rows are sampled randomly.
    """
    mother_pid: Optional[int] = None
    child_pid: Optional[int] = None

    E: Range = Range()
    pt: Range = Range()
    p: Range = Range()
    px: Range = Range()
    py: Range = Range()
    pz: Range = Range()
    eta: Range = Range()
    phi: Range = Range()
    theta: Range = Range()
    met: Range = Range()

    max_rows: Optional[int] = 200_000

def _has_pid(listcol: pd.Series, pid: int) -> pd.Series:
    """Check whether each tuple-like cell contains a given PDG ID.

    Args:
        listcol: Series whose elements are expected to be tuples of integers.
        pid: PDG ID to search for.

    Returns:
        A boolean mask indicating whether ``pid`` is present in each row.
    """
    return listcol.apply(lambda xs: pid in xs if xs is not None else False)

def apply_filters(df: pd.DataFrame, spec: ParticleFilterSpec) -> pd.DataFrame:
    """Filter a particle DataFrame according to a filter specification.

    Topological constraints are applied first, then numeric range filters are
    evaluated on the columns that exist in the input DataFrame. When the
    filtered result exceeds ``spec.max_rows``, a reproducible random sample is
    returned.

    Args:
        df: Input particle table.
        spec: Filtering configuration.

    Returns:
        A filtered copy of ``df``. If ``df`` is empty, it is returned unchanged.
    """
    if df.empty:
        return df

    m = pd.Series(True, index=df.index)

    if spec.mother_pid is not None:
        m &= _has_pid(df["mother_pids"], int(spec.mother_pid))

    if spec.child_pid is not None:
        m &= _has_pid(df["child_pids"], int(spec.child_pid))

    for col, rng in [
        ("E", spec.E),
        ("pt", spec.pt),
        ("p", spec.p),
        ("px", spec.px),
        ("py", spec.py),
        ("pz", spec.pz),
        ("eta", spec.eta),
        ("phi", spec.phi),
        ("theta", spec.theta),
        ("met", spec.met),
    ]:
        if col in df.columns:
            m &= rng.contains(df[col])

    out = df.loc[m].copy()

    if spec.max_rows is not None and len(out) > spec.max_rows:
        out = out.sample(spec.max_rows, random_state=0)

    return out
