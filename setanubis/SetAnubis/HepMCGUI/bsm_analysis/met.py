from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Protocol, Sequence
import numpy as np

class METCalculator(Protocol):
    """Protocol for MET computation strategies."""
    def met(self, event: "hp.GenEvent") -> float:
        """Compute the missing transverse energy for one event.

        Args:
            event: HepMC event to evaluate.

        Returns:
            The event MET value.
        """
        ...

@dataclass(frozen=True)
class SimpleTruthMET:
    """Compute truth-level missing transverse energy.

    The MET is built from the vector sum of visible final-state particles in
    the transverse plane:

    - only particles with ``status == final_state_status`` are considered,
    - particles whose absolute PDG ID is listed in ``invisible_abs_pids``
      are excluded,
    - the returned value is ``sqrt(sum_px**2 + sum_py**2)``.

    Attributes:
        final_state_status: Status code used to identify final-state particles.
        invisible_abs_pids: Absolute PDG IDs treated as invisible. By default,
            neutrinos are excluded.
    """
    final_state_status: int = 1
    invisible_abs_pids: Sequence[int] = (12, 14, 16)

    def met(self, event: "hp.GenEvent") -> float:
        """Compute truth-level MET for a single event.

        Args:
            event: HepMC event to process.

        Returns:
            The scalar missing transverse energy.

        Notes:
            Particles with unreadable status or momentum information are
            skipped silently.
        """
        import pyhepmc as hp  # noqa
        px_sum = 0.0
        py_sum = 0.0
        for p in event.particles:
            try:
                if p.status != self.final_state_status:
                    continue
            except Exception:
                continue
            if abs(int(p.pid)) in self.invisible_abs_pids:
                continue
            mom = p.momentum
            px = mom.px() if callable(getattr(mom, "px", None)) else mom.px
            py = mom.py() if callable(getattr(mom, "py", None)) else mom.py
            px_sum += float(px)
            py_sum += float(py)
        return float(np.hypot(px_sum, py_sum))
