from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple
import numpy as np
import pandas as pd

from .sources import EventSource, hepmc_unit_name
from .met import METCalculator, SimpleTruthMET

_LENGTH_TO_METRES = {
    None: 1.0,
    "MM": 1e-3,
    "CM": 1e-2,
    "M": 1.0,
    "METRE": 1.0,
}

def _call_or_attr(obj, name: str) -> float:
    """Return an attribute value as a float, calling it if needed.

    This helper supports HepMC Python bindings that may expose values either
    as plain attributes or as zero-argument methods.

    Args:
        obj: Object exposing the requested attribute.
        name: Attribute name to read.

    Returns:
        The attribute value converted to ``float``.
    """
    v = getattr(obj, name)
    return float(v() if callable(v) else v)

def _safe_pid_list(particles: Iterable["hp.GenParticle"]) -> Tuple[int, ...]:
    """Extract PDG IDs from a particle iterable.

    Any particle whose ``pid`` cannot be read or converted to ``int`` is
    silently skipped.

    Args:
        particles: Iterable of HepMC particles.

    Returns:
        A tuple of PDG IDs.
    """
    out: List[int] = []
    for p in particles:
        try:
            out.append(int(p.pid))
        except Exception:
            continue
    return tuple(out)

def _vertex_xyzt(vtx: object) -> Optional[Tuple[float, float, float, float]]:
    """Extract a vertex position as ``(x, y, z, t)``.

    The function supports multiple HepMC binding styles. It first tries
    ``vertex.position.x/y/z/t`` and falls back to ``vertex.x/y/z/t``.

    The time-like component is interpreted as ``c*t`` and therefore carries
    the same HepMC length unit as the spatial coordinates.

    Args:
        vtx: HepMC vertex-like object.

    Returns:
        A 4-tuple ``(x, y, z, t)`` if the position can be read, otherwise
        ``None``.
    """
    if vtx is None:
        return None
    pos = getattr(vtx, "position", None)
    try:
        if pos is not None:
            x = _call_or_attr(pos, "x")
            y = _call_or_attr(pos, "y")
            z = _call_or_attr(pos, "z")
            t = _call_or_attr(pos, "t")
            return (x, y, z, t)
    except Exception:
        pass
    try:
        x = _call_or_attr(vtx, "x")
        y = _call_or_attr(vtx, "y")
        z = _call_or_attr(vtx, "z")
        t = _call_or_attr(vtx, "t")
        return (x, y, z, t)
    except Exception:
        return None

def _production_vertex(p: "hp.GenParticle") -> Optional[object]:
    """Return the production vertex of a HepMC particle.

    This helper supports bindings where ``production_vertex`` is either an
    attribute or a zero-argument method.

    Args:
        p: HepMC particle.

    Returns:
        The production vertex object, or ``None`` if unavailable.
    """
    v = getattr(p, "production_vertex", None)
    if callable(v):
        try:
            return v()
        except Exception:
            return None
    return v

def _end_vertex(p: "hp.GenParticle") -> Optional[object]:
    """Return the end vertex of a HepMC particle.

    This helper supports bindings where ``end_vertex`` is either an
    attribute or a zero-argument method.

    Args:
        p: HepMC particle.

    Returns:
        The end vertex object, or ``None`` if unavailable.
    """
    v = getattr(p, "end_vertex", None)
    if callable(v):
        try:
            return v()
        except Exception:
            return None
    return v

@dataclass
class ExtractionConfig:
    """Configuration for particle extraction from an event source.

    Attributes:
        pdg_id: PDG ID of the particle species to extract.
        max_events: Maximum number of events to process. If ``None``, all
            available events are processed.
        status: Optional HepMC particle status filter.
        ignore_self_decays: Whether to remove self-references to ``pdg_id``
            from mother and child PID lists.
        hepmc_positions_are_ip_relative: Whether HepMC vertex positions are
            assumed to be expressed relative to the interaction point.
        default_length_unit: Fallback HepMC length unit used when the event
            does not specify one.
        position_transform: Optional callable applied after conversion to
            metres. It must accept ``(x, y, z)`` and return transformed
            coordinates in metres.
        met_calculator: Strategy used to compute one MET value per event.
    """
    pdg_id: int
    max_events: Optional[int] = None
    status: Optional[int] = None
    ignore_self_decays: bool = True

    hepmc_positions_are_ip_relative: bool = True
    default_length_unit: str = "MM"

    position_transform: Optional[callable] = None  # (x,y,z)->(x,y,z) in metres

    met_calculator: METCalculator = SimpleTruthMET()

class ParticleExtractor:
    """Extract a particle-level table from an event source.

    This class converts HepMC events into a tidy pandas ``DataFrame`` where
    each row corresponds to one particle matching the requested PDG ID.

    Responsibilities are intentionally limited to:
    - event traversal,
    - particle selection,
    - unit conversion,
    - event-level MET attachment.

    No plotting or UI logic is included.
    """

    def __init__(self, source: EventSource):
        """Initialize the extractor.

        Args:
            source: Event source yielding HepMC events.
        """
        self._source = source

    def extract(self, cfg: ExtractionConfig) -> pd.DataFrame:
        """Extract particles matching a configuration into a DataFrame.

        For each matching particle, this method records identifiers,
        kinematics, ancestry information, production and decay vertices, and
        attaches one event-level MET value.

        Position coordinates are converted to metres using the event length
        unit when available, otherwise ``cfg.default_length_unit`` is used.

        Args:
            cfg: Extraction parameters controlling particle selection, event
                limits, coordinate handling, and MET computation.

        Returns:
            A pandas ``DataFrame`` containing one row per selected particle.
            The returned table may include the following columns:

            - ``event``
            - ``particle_index``
            - ``pid``
            - ``status``
            - ``momentum_unit``
            - ``length_unit``
            - ``E``, ``pt``, ``p``, ``px``, ``py``, ``pz``
            - ``eta``, ``phi``, ``theta``
            - ``mother_pids``, ``child_pids``
            - ``prod_x_m``, ``prod_y_m``, ``prod_z_m``, ``prod_ct_m``
            - ``dec_x_m``, ``dec_y_m``, ``dec_z_m``, ``dec_ct_m``
            - ``met``

            If no particle matches, an empty ``DataFrame`` is returned.

        Notes:
            MET is computed once per processed event. If MET computation fails
            for an event, the corresponding value is stored as ``NaN``.
        """
        import pyhepmc as hp  # noqa

        rows: List[Dict[str, object]] = []
        met_by_event: Dict[int, float] = {}

        n_events = 0
        for i_event, event in enumerate(self._source):
            if cfg.max_events is not None and n_events >= cfg.max_events:
                break
            n_events += 1

            mom_unit = hepmc_unit_name(event, "momentum_unit")
            len_unit = hepmc_unit_name(event, "length_unit")
            if len_unit is None:
                len_unit = cfg.default_length_unit
            pos_scale = _LENGTH_TO_METRES.get(len_unit, 1.0)

            # MET once per event
            try:
                met_by_event[i_event] = float(cfg.met_calculator.met(event))
            except Exception:
                met_by_event[i_event] = float("nan")

            for i_part, p in enumerate(event.particles):
                try:
                    if int(p.pid) != int(cfg.pdg_id):
                        continue
                    if cfg.status is not None and int(p.status) != int(cfg.status):
                        continue
                except Exception:
                    continue

                mom = p.momentum
                px = _call_or_attr(mom, "px")
                py = _call_or_attr(mom, "py")
                pz = _call_or_attr(mom, "pz")
                E  = _call_or_attr(mom, "e")

                pt    = _call_or_attr(mom, "pt")
                eta   = _call_or_attr(mom, "eta")
                phi   = _call_or_attr(mom, "phi")
                theta = _call_or_attr(mom, "theta")
                p_abs = float(np.sqrt(px*px + py*py + pz*pz))

                mothers = _safe_pid_list(getattr(p, "parents", []))
                childs  = _safe_pid_list(getattr(p, "children", []))

                if cfg.ignore_self_decays:
                    mothers = tuple(pid for pid in mothers if pid != int(cfg.pdg_id))
                    childs  = tuple(pid for pid in childs  if pid != int(cfg.pdg_id))

                prod_v = _vertex_xyzt(_production_vertex(p))
                end_v  = _vertex_xyzt(_end_vertex(p))

                def _convert(v):
                    if v is None:
                        return (np.nan, np.nan, np.nan, np.nan)
                    x, y, z, ct = (v[0]*pos_scale, v[1]*pos_scale, v[2]*pos_scale, v[3]*pos_scale)
                    if cfg.position_transform is not None:
                        x, y, z = cfg.position_transform(x, y, z)
                    return (x, y, z, ct)

                prod_x, prod_y, prod_z, prod_ct = _convert(prod_v)
                dec_x, dec_y, dec_z, dec_ct = _convert(end_v)

                rows.append({
                    "event": i_event,
                    "particle_index": i_part,
                    "pid": int(cfg.pdg_id),
                    "status": int(getattr(p, "status", -999)),
                    "momentum_unit": mom_unit,
                    "length_unit": len_unit,
                    "E": float(E),
                    "pt": float(pt),
                    "p": float(p_abs),
                    "px": float(px),
                    "py": float(py),
                    "pz": float(pz),
                    "eta": float(eta),
                    "phi": float(phi),
                    "theta": float(theta),
                    "mother_pids": mothers,
                    "child_pids": childs,
                    "prod_x_m": float(prod_x),
                    "prod_y_m": float(prod_y),
                    "prod_z_m": float(prod_z),
                    "prod_ct_m": float(prod_ct),
                    "dec_x_m": float(dec_x),
                    "dec_y_m": float(dec_y),
                    "dec_z_m": float(dec_z),
                    "dec_ct_m": float(dec_ct),
                })

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        df["met"] = df["event"].map(met_by_event).astype(float)
        return df
