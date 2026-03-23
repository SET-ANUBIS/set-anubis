from __future__ import annotations

from functools import lru_cache
from typing import Optional, Tuple

try:
    from particle import Particle 
except Exception: 
    Particle = None 


@lru_cache(maxsize=20000)
def particle_name(pid: int) -> str:
    """Return a human-readable particle name for a PDG ID.

    Args:
        pid: PDG ID.

    Returns:
        A particle name from the ``particle`` package when available.
        Falls back to ``"PDG <pid>"`` when the package is unavailable or the
        identifier cannot be resolved.
    """
    if Particle is None:
        return f"PDG {pid}"
    try:
        p = Particle.from_pdgid(int(pid))
        return getattr(p, "name", None) or getattr(p, "latex_name", None) or f"PDG {pid}"
    except Exception:
        return f"PDG {pid}"


@lru_cache(maxsize=20000)
def particle_charge(pid: int) -> Optional[float]:
    """Return the electric charge associated with a PDG ID.

    Args:
        pid: PDG ID.

    Returns:
        The electric charge in units of ``e`` when known, otherwise ``None``.
    """
    if Particle is None:
        return None
    try:
        p = Particle.from_pdgid(int(pid))
        q = getattr(p, "charge", None)
        if q is None:
            return None
        return float(q)
    except Exception:
        return None


@lru_cache(maxsize=20000)
def is_charged(pid: int) -> Optional[bool]:
    """Tell whether a particle is electrically charged.

    Args:
        pid: PDG ID.

    Returns:
        ``True`` when the particle charge is non-zero, ``False`` when it is
        known to be neutral, and ``None`` when the charge cannot be resolved.
    """
    q = particle_charge(pid)
    if q is None:
        return None
    return abs(q) > 1e-12


@lru_cache(maxsize=20000)
def particle_display_name(pid: int) -> str:
    """Return a short display label for a PDG ID.

    Args:
        pid: PDG ID.

    Returns:
        A compact particle label such as a PDG name when available, otherwise
        a fallback string of the form ``"PDG <pid>"``.
    """
    if Particle is None:
        return f"PDG {pid}"
    try:
        p = Particle.from_pdgid(int(pid))
        nm = getattr(p, "pdg_name", None) or getattr(p, "name", None)
        if nm:
            return str(nm)
        ln = getattr(p, "latex_name", None)
        if ln:
            return str(ln)
    except Exception:
        pass
    return f"PDG {pid}"
