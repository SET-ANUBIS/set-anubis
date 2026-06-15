from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import numpy as np

from .particle_info import particle_name, particle_display_name, is_charged

_LENGTH_TO_METRES = {
    None: 1.0,
    "MM": 1e-3,
    "CM": 1e-2,
    "M": 1.0,
    "METRE": 1.0,
}

def _call_or_attr(obj, name: str) -> float:
    """Return an attribute value as a float, calling it if needed.

    Args:
        obj: Object exposing the requested attribute.
        name: Attribute name to read.

    Returns:
        The attribute value converted to ``float``.
    """
    v = getattr(obj, name)
    return float(v() if callable(v) else v)

def _hepmc_unit_name(obj: object, attr: str) -> Optional[str]:
    """Safely read the name of a HepMC unit enum attribute.

    Args:
        obj: Object holding the unit attribute.
        attr: Name of the attribute to inspect.

    Returns:
        The enum name as a string, or ``None`` if unavailable.
    """
    try:
        u = getattr(obj, attr)
    except Exception:
        return None
    try:
        return getattr(u, "name", None)
    except Exception:
        return None

def _vertex_xyz(vtx: object) -> Optional[Tuple[float, float, float]]:
    """Extract a vertex position as ``(x, y, z)``.

    Args:
        vtx: HepMC vertex-like object.

    Returns:
        A 3-tuple ``(x, y, z)`` if the position can be read, otherwise
        ``None``.
    """
    if vtx is None:
        return None
    pos = getattr(vtx, "position", None)
    try:
        if pos is not None:
            return (_call_or_attr(pos, "x"), _call_or_attr(pos, "y"), _call_or_attr(pos, "z"))
    except Exception:
        pass
    try:
        return (_call_or_attr(vtx, "x"), _call_or_attr(vtx, "y"), _call_or_attr(vtx, "z"))
    except Exception:
        return None

def _production_vertex(p: "hp.GenParticle") -> Optional[object]:
    """Return the production vertex of a HepMC particle.

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

def _momentum_xyz(p: "hp.GenParticle") -> Tuple[float, float, float]:
    """Return particle momentum components as ``(px, py, pz)``.

    The function first tries to read Cartesian momentum components directly.
    If that fails, it reconstructs them from ``p``, ``theta``, and ``phi``.

    Args:
        p: HepMC particle.

    Returns:
        A 3-tuple ``(px, py, pz)``. Returns ``(0.0, 0.0, 0.0)`` if momentum
        cannot be recovered.
    """
    mom = p.momentum

    try:
        px = _call_or_attr(mom, "px")
        py = _call_or_attr(mom, "py")
        pz = _call_or_attr(mom, "pz")
        if np.isfinite(px) and np.isfinite(py) and np.isfinite(pz):
            return px, py, pz
    except Exception:
        pass

    try:
        pabs = _call_or_attr(mom, "p")
        theta = _call_or_attr(mom, "theta")
        phi = _call_or_attr(mom, "phi")
        px = pabs * np.sin(theta) * np.cos(phi)
        py = pabs * np.sin(theta) * np.sin(phi)
        pz = pabs * np.cos(theta)
        return float(px), float(py), float(pz)
    except Exception:
        return 0.0, 0.0, 0.0

def _normalize(v: np.ndarray) -> np.ndarray:
    """Return the normalized version of a vector.

    Args:
        v: Input vector.

    Returns:
        The unit vector in the same direction as ``v``. If the norm is
        non-finite or zero, a zero vector of the same shape is returned.
    """
    n = np.linalg.norm(v)
    if not np.isfinite(n) or n <= 0:
        return np.zeros_like(v)
    return v / n


def _particles_out(vtx: object) -> List["hp.GenParticle"]:
    """Return outgoing particles from a vertex.

    The helper supports multiple HepMC binding conventions such as
    ``particles_out`` and ``particles_outgoing``.

    Args:
        vtx: HepMC vertex-like object.

    Returns:
        A list of outgoing particles. Returns an empty list if the outgoing
        particles cannot be read.
    """
    if vtx is None:
        return []
    out = getattr(vtx, "particles_out", None)
    if out is None:
        out = getattr(vtx, "particles_outgoing", None)
    if out is None:
        return []
    try:
        if callable(out):
            out = out()
        return list(out)
    except Exception:
        try:
            return list(out)
        except Exception:
            return []

def _get_children(p: "hp.GenParticle") -> List["hp.GenParticle"]:
    """Return child particles for decay-tree construction.

    The preferred definition of decay products is the set of outgoing
    particles attached to the particle end vertex. If unavailable, the helper
    falls back to ``p.children`` when present.

    Args:
        p: HepMC particle.

    Returns:
        A list of child particles.
    """
    ev = _end_vertex(p)
    if ev is not None:
        out = _particles_out(ev)
        if len(out) > 0:
            return out

    try:
        ch = getattr(p, "children", None)
        return list(ch) if ch is not None else []
    except Exception:
        return []


def ray_box_intersection(
    p0: np.ndarray,
    d: np.ndarray,
    bounds: Tuple[float, float, float, float, float, float],
) -> Optional[np.ndarray]:
    """Intersect a ray with an axis-aligned box.

    The ray is defined as ``p(t) = p0 + t * d`` for ``t >= 0``. The nearest
    valid intersection point is returned.

    Args:
        p0: Ray origin as a 3D vector.
        d: Ray direction as a 3D vector.
        bounds: Box bounds given as
            ``(xmin, xmax, ymin, ymax, zmin, zmax)``.

    Returns:
        The nearest intersection point as a NumPy array, or ``None`` if the
        ray does not intersect the box.

    Notes:
        The implementation uses the slab method and handles zero direction
        components safely.
    """
    xmin, xmax, ymin, ymax, zmin, zmax = bounds

    tmin = 0.0
    tmax = float("inf")
    for i, (p, di, lo, hi) in enumerate([
        (p0[0], d[0], xmin, xmax),
        (p0[1], d[1], ymin, ymax),
        (p0[2], d[2], zmin, zmax),
    ]):
        if abs(di) < 1e-12:
            if p < lo or p > hi:
                return None
            continue
        t1 = (lo - p) / di
        t2 = (hi - p) / di
        t_enter = min(t1, t2)
        t_exit = max(t1, t2)
        tmin = max(tmin, t_enter)
        tmax = min(tmax, t_exit)
        if tmax < tmin:
            return None
    if not np.isfinite(tmin):
        return None
    if tmin < 0:
        if not np.isfinite(tmax) or tmax < 0:
            return None
        t = tmax
    else:
        t = tmin
    return p0 + t * d

def _stable_endpoint_from_momentum(
    start: np.ndarray,
    p: "hp.GenParticle",
    bounds: Tuple[float, float, float, float, float, float],
    extend_m: float,
    min_length_m: float = 3.0,
) -> np.ndarray:
    """Build a visible endpoint for a particle without an end vertex.

    The endpoint is computed from the particle momentum direction. The method
    first tries a ray-box intersection and falls back to a straight extension
    if no suitable hit is found.

    Args:
        start: Segment start position in metres.
        p: HepMC particle.
        bounds: Display bounds given as
            ``(xmin, xmax, ymin, ymax, zmin, zmax)``.
        extend_m: Fallback extension length in metres.
        min_length_m: Minimum visible segment length in metres.

    Returns:
        A 3D endpoint position in metres.

    Notes:
        The returned point is guaranteed to define a segment with non-zero
        visible length.
    """
    px, py, pz = _momentum_xyz(p)
    d = _normalize(np.array([px, py, pz], dtype=float))

    if not np.isfinite(d).all() or np.linalg.norm(d) < 1e-12:
        d = np.array([1.0, 0.2, 0.1], dtype=float)
        d = _normalize(d)

    hit = ray_box_intersection(start, d, bounds)

    if hit is None or np.linalg.norm(hit - start) < min_length_m:
        L = max(float(extend_m), float(min_length_m))
        hit = start + d * L

    return hit


@dataclass(frozen=True)
class TrackSegment:
    """Geometric representation of a particle track segment.

    Attributes:
        pid: PDG ID of the particle.
        name: Human-readable particle label.
        charged: Whether the particle is charged, if known.
        depth: Depth in the decay tree relative to the selected root.
        is_root: Whether the segment corresponds to a root particle.
        x0: Segment start x coordinate in metres.
        y0: Segment start y coordinate in metres.
        z0: Segment start z coordinate in metres.
        x1: Segment end x coordinate in metres.
        y1: Segment end y coordinate in metres.
        z1: Segment end z coordinate in metres.
        has_decay_vertex: Whether the segment end comes from an actual decay
            vertex rather than a synthetic extrapolated endpoint.
    """
    pid: int
    name: str
    charged: Optional[bool]
    depth: int
    is_root: bool  # BSM root or not

    x0: float
    y0: float
    z0: float
    x1: float
    y1: float
    z1: float

    has_decay_vertex: bool

    # Decay-tree metadata used by the UI to build an explanatory tree.
    node_id: int = -1
    parent_id: Optional[int] = None
    copy_count: int = 0


@dataclass(frozen=True)
class TrackBuildConfig:
    """Configuration for building event track segments.

    Attributes:
        root_pdg: PDG ID used to select root particles in the event.
        max_depth: Maximum recursion depth in the decay tree.
        extend_m: Fallback extrapolation length in metres for particles
            without an end vertex.
        default_length_unit: Fallback HepMC length unit used when the event
            does not specify one.
        position_transform: Optional callable applied after conversion to
            metres. It must accept ``(x, y, z)`` and return transformed
            coordinates in metres.
        bounds_m: Display bounds used to extrapolate stable particles, given
            as ``(xmin, xmax, ymin, ymax, zmin, zmax)`` in metres.
    """
    root_pdg: int
    max_depth: int = 2  # daughters + granddaughters
    # If a particle is stable (no end_vertex), we extend its direction to the viewing bounds.
    # If we can't intersect the bounds (e.g. zero momentum), fall back to this value.
    extend_m: float = 8.0
    default_length_unit: str = "MM"
    position_transform: Optional[callable] = None  # metres -> metres

    # bounds used when a particle has no end_vertex
    bounds_m: Tuple[float, float, float, float, float, float] = (-18, 18, -18, 25, -30, 30)


def build_event_tracks(event: "hp.GenEvent", cfg: TrackBuildConfig) -> List[TrackSegment]:
    """Build track segments for root particles and their descendants.

    For every particle in the event whose PDG ID matches ``cfg.root_pdg``,
    this function builds one segment and recursively follows its descendants
    up to ``cfg.max_depth``.

    Segment geometry follows these rules:
    - start point comes from the production vertex when available,
    - end point comes from the end vertex when available,
    - if no end vertex exists, the segment is extrapolated using the particle
      momentum direction and the configured display bounds.

    All positions are converted to metres before optional coordinate
    transformation.

    Args:
        event: HepMC event to process.
        cfg: Track-building configuration.

    Returns:
        A list of ``TrackSegment`` objects describing the visible decay tree.

    Notes:
        Daughter start positions prefer their own production vertex. If that
        is missing, the parent end vertex is used as a fallback, then the
        parent start position as a last resort.
    """
    import pyhepmc as hp  # noqa

    len_unit = _hepmc_unit_name(event, "length_unit") or cfg.default_length_unit
    scale = _LENGTH_TO_METRES.get(len_unit, 1.0)

    def convert_pos(v: Optional[Tuple[float, float, float]]) -> Optional[np.ndarray]:
        if v is None:
            return None
        p = np.array([v[0] * scale, v[1] * scale, v[2] * scale], dtype=float)
        if cfg.position_transform is not None:
            x, y, z = cfg.position_transform(float(p[0]), float(p[1]), float(p[2]))
            p = np.array([x, y, z], dtype=float)
        return p

    segs: List[TrackSegment] = []
    next_node_id = 0

    def _same_pid(a: "hp.GenParticle", b: "hp.GenParticle") -> bool:
        try:
            return int(a.pid) == int(b.pid)
        except Exception:
            return False

    def _particle_seen_key(p: "hp.GenParticle") -> int:
        # Object identity is stable enough for a single in-memory event and
        # avoids relying on binding-specific barcode/id attributes.
        return id(p)

    def collapse_self_copies(p: "hp.GenParticle", max_links: int = 128) -> Tuple["hp.GenParticle", int]:
        """Follow status/self-copy links without consuming display depth.

        Generators often represent propagation with chains like LLP -> LLP ->
        LLP before the actual decay. Drawing each copy makes the `depth` control
        look ineffective and can stop the tree before the visible daughters.
        We collapse only pure self-copy vertices, i.e. vertices whose outgoing
        particles contain same-PDG copies and no non-self decay products.
        """
        current = p
        seen = {_particle_seen_key(current)}
        n_copies = 0

        for _ in range(max_links):
            children = _get_children(current)
            if not children:
                break

            same_children = [ch for ch in children if _same_pid(ch, current)]
            non_same_children = [ch for ch in children if not _same_pid(ch, current)]

            # A real decay vertex should expose non-self products. Stop there.
            if non_same_children or not same_children:
                break

            nxt = same_children[0]
            key = _particle_seen_key(nxt)
            if key in seen:
                break
            seen.add(key)
            current = nxt
            n_copies += 1

        return current, n_copies

    def make_segment(
        p: "hp.GenParticle",
        depth: int,
        is_root: bool,
        node_id: int,
        parent_id: Optional[int],
        start_override: Optional[np.ndarray] = None,
        source_particle: Optional["hp.GenParticle"] = None,
        copy_count: int = 0,
    ) -> Optional[TrackSegment]:
        """Build one visible track segment for a particle.

        `source_particle` is used for the production vertex. This lets a
        collapsed LLP/self-copy chain be drawn from its original creation point
        to the terminal decay vertex of the last copy.
        """
        source = source_particle if source_particle is not None else p
        pv = start_override if start_override is not None else convert_pos(_vertex_xyz(_production_vertex(source)))
        if pv is None:
            pv = convert_pos(_vertex_xyz(_production_vertex(p)))
        if pv is None:
            return None

        ev_xyz = _vertex_xyz(_end_vertex(p))
        ev = convert_pos(ev_xyz)

        has_decay = ev is not None
        if ev is None:
            ev = _stable_endpoint_from_momentum(
                start=pv,
                p=p,
                bounds=cfg.bounds_m,
                extend_m=cfg.extend_m,
                min_length_m=3.0,
            )

        pid = int(getattr(p, "pid", 0))

        return TrackSegment(
            pid=pid,
            name=particle_display_name(pid),
            charged=is_charged(pid),
            depth=depth,
            is_root=is_root,
            x0=float(pv[0]), y0=float(pv[1]), z0=float(pv[2]),
            x1=float(ev[0]), y1=float(ev[1]), z1=float(ev[2]),
            has_decay_vertex=has_decay,
            node_id=node_id,
            parent_id=parent_id,
            copy_count=copy_count,
        )

    def walk(
        p: "hp.GenParticle",
        depth: int,
        is_root: bool,
        start_override: Optional[np.ndarray] = None,
        parent_id: Optional[int] = None,
        source_particle: Optional["hp.GenParticle"] = None,
    ):
        """Recursively traverse descendants and collect visible track segments."""
        nonlocal next_node_id

        if depth > cfg.max_depth:
            return

        visible_particle, copy_count = collapse_self_copies(p)
        node_id = next_node_id
        next_node_id += 1

        seg = make_segment(
            visible_particle,
            depth=depth,
            is_root=is_root,
            node_id=node_id,
            parent_id=parent_id,
            start_override=start_override,
            source_particle=source_particle or p,
            copy_count=copy_count,
        )

        this_parent_id = parent_id
        if seg is not None:
            segs.append(seg)
            this_parent_id = node_id

        if depth == cfg.max_depth:
            return

        children = _get_children(visible_particle)

        parent_end = convert_pos(_vertex_xyz(_end_vertex(visible_particle)))
        parent_start = None
        if seg is not None:
            parent_start = np.array([seg.x0, seg.y0, seg.z0], dtype=float)

        for ch in children:
            # Same-PDG children that still exist here are display copies; do not
            # consume a new depth level for them. Follow them at the same depth.
            if _same_pid(ch, visible_particle):
                walk(
                    ch,
                    depth=depth,
                    is_root=is_root,
                    start_override=start_override,
                    parent_id=parent_id,
                    source_particle=source_particle or p,
                )
                continue

            # Priority:
            # 1) daughter's own production vertex
            # 2) parent's terminal end vertex
            # 3) parent's start vertex
            child_pv = convert_pos(_vertex_xyz(_production_vertex(ch)))
            child_start = child_pv if child_pv is not None else parent_end
            if child_start is None:
                child_start = parent_start

            walk(ch, depth + 1, is_root=False, start_override=child_start, parent_id=this_parent_id)

    for p in event.particles:
        try:
            if int(p.pid) == int(cfg.root_pdg):
                # Draw only physical roots. If the same-PDG particle is itself
                # produced by a pure self-copy vertex, it will be reached by the
                # first root's collapsed chain.
                parents = []
                try:
                    parents = list(getattr(p, "parents", []))
                except Exception:
                    parents = []
                if any(_same_pid(parent, p) for parent in parents):
                    continue
                walk(p, depth=0, is_root=True, start_override=None, parent_id=None, source_particle=p)
        except Exception:
            continue

    return segs
