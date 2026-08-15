from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, Optional, Tuple

import os
import threading

import numpy as np
import pandas as pd
import awkward as ak
import fastjet


_NATIVE_OUTPUT_LOCK = threading.Lock()


def _env_fastjet_banner_default() -> bool:
    value = os.getenv("SETANUBIS_FASTJET_BANNER", "0").strip().lower()
    return value in {"1", "true", "yes", "on", "show"}


@contextmanager
def _suppress_fastjet_banner(enabled: bool) -> Iterator[None]:
    """Temporarily suppress native FastJet output when requested.

    SET-ANUBIS keeps the FastJet console banner quiet by default to avoid noisy
    batch and notebook output. Users can restore the upstream banner with
    ``JetClusteringConfig(show_banner=True)`` or
    ``SETANUBIS_FASTJET_BANNER=1``. This setting only controls console output;
    FastJet must still be cited in scientific work.
    """

    if not enabled:
        yield
        return

    # FastJet's banner stream is process-global. Serialising the short context
    # avoids races when multiple SET-ANUBIS threads cluster their first event.
    with _NATIVE_OUTPUT_LOCK:
        cluster_sequence = getattr(fastjet, "ClusterSequence", None)
        setter = getattr(cluster_sequence, "set_fastjet_banner_stream", None)
        getter = getattr(cluster_sequence, "fastjet_banner_stream", None)
        if callable(setter) and callable(getter):
            try:
                previous = getter()
                setter(None)
            except (TypeError, RuntimeError):
                pass
            else:
                try:
                    yield
                finally:
                    setter(previous)
                return

        # Some Python wheels do not expose the C++ stream setter. Redirecting
        # the native file descriptors is a narrow fallback around the first
        # clustering call.
        stdout_fd = 1
        stderr_fd = 2
        saved_stdout = os.dup(stdout_fd)
        saved_stderr = os.dup(stderr_fd)
        try:
            with open(os.devnull, "w", encoding="utf-8") as sink:
                os.dup2(sink.fileno(), stdout_fd)
                os.dup2(sink.fileno(), stderr_fd)
                yield
        finally:
            os.dup2(saved_stdout, stdout_fd)
            os.dup2(saved_stderr, stderr_fd)
            os.close(saved_stdout)
            os.close(saved_stderr)



def _pt(px: np.ndarray, py: np.ndarray) -> np.ndarray:
    return np.sqrt(px * px + py * py)

def _p(px: np.ndarray, py: np.ndarray, pz: np.ndarray) -> np.ndarray:
    return np.sqrt(px * px + py * py + pz * pz)


class _EventRowIndex:
    """Compact event -> row-position lookup for one final-state dataframe.

    ``JetDFBuilder`` used to keep one pandas ``DataFrame`` object per event in
    two dictionaries (charged and neutral).  For large samples, the Python and
    pandas object overhead can exceed the actual particle data by a large
    factor.  This helper stores only one stable sort permutation plus one small
    event -> slice table and creates temporary NumPy arrays for the event being
    clustered.

    Row order inside each event is preserved exactly.
    """

    __slots__ = ("_order", "_event_slices", "_arrays", "_empty")

    _KINEMATIC_COLUMNS = ("px", "py", "pz", "E")

    def __init__(self, df: Optional[pd.DataFrame]) -> None:
        if df is None or df.empty:
            self._order = np.empty(0, dtype=np.intp)
            self._event_slices: Dict[int, Tuple[int, int]] = {}
            self._arrays: Dict[str, np.ndarray] = {}
            self._empty = True
            return

        events = df["eventNumber"].to_numpy(dtype=np.int64, copy=False)
        # Stable sorting is important: the historical pandas groupby kept the
        # original particle order inside each event.
        order = np.argsort(events, kind="stable")
        sorted_events = events[order]

        starts = np.flatnonzero(
            np.r_[True, sorted_events[1:] != sorted_events[:-1]]
        )
        ends = np.r_[starts[1:], len(sorted_events)]

        self._order = order
        self._event_slices = {
            int(sorted_events[start]): (int(start), int(end))
            for start, end in zip(starts, ends)
        }
        self._arrays = {
            name: df[name].to_numpy(copy=False)
            for name in (*self._KINEMATIC_COLUMNS, "weight")
            if name in df.columns
        }
        self._empty = False

    def positions(self, event: int) -> np.ndarray:
        if self._empty:
            return self._order[:0]
        span = self._event_slices.get(int(event))
        if span is None:
            return self._order[:0]
        start, end = span
        # This is a view of the permutation, not a new per-event DataFrame.
        return self._order[start:end]

    def has_event(self, event: int) -> bool:
        return int(event) in self._event_slices

    def has_column(self, name: str) -> bool:
        return name in self._arrays

    def values(self, event: int, name: str, *, dtype=float) -> np.ndarray:
        positions = self.positions(event)
        if positions.size == 0:
            return np.empty(0, dtype=dtype)
        values = self._arrays[name][positions]
        return values.astype(dtype, copy=False)

    def first_value(self, event: int, name: str):
        positions = self.positions(event)
        if positions.size == 0:
            raise IndexError("event has no rows")
        return self._arrays[name][int(positions[0])]


@dataclass(frozen=True)
class JetClusteringConfig:
    """Configuration for FastJet clustering.

    ``show_banner`` defaults to ``False`` so that library and batch output stays
    concise. Users may explicitly enable the upstream FastJet banner. This
    option does not change the clustering algorithm or citation requirements.
    """

    R: float = 0.4
    algorithm: int = fastjet.antikt_algorithm
    show_banner: bool = field(default_factory=_env_fastjet_banner_default)


class JetClustering:
    """
    fastjet encapsulation for event clustering from a px,py,pz,E table.
    """
    def __init__(self, cfg: Optional[JetClusteringConfig] = None) -> None:
        self.cfg = cfg or JetClusteringConfig()
        self._def = fastjet.JetDefinition(self.cfg.algorithm, self.cfg.R)

    def cluster_event(self, px: np.ndarray, py: np.ndarray, pz: np.ndarray, E: np.ndarray):
        """
        Return list of fastjet jets (PseudoJets) for a given event.
        """
        # fastjet AwkwardClusterSequence want an array with px,py,pz,E
        arr = np.rec.fromarrays(
            [px, py, pz, E],
            names=["px", "py", "pz", "E"],
            dtype=[("px", float), ("py", float), ("pz", float), ("E", float)],
        )
        ak_arr = ak.from_numpy(arr)
        with _suppress_fastjet_banner(enabled=not self.cfg.show_banner):
            seq = fastjet._pyjet.AwkwardClusterSequence(ak_arr, self._def)
            return seq.inclusive_jets()



class JetDFBuilder:
    """
    Construct a DataFrame of jets from final states (neutral/charged).
    
    """
    def __init__(self, clustering: Optional[JetClustering] = None) -> None:
        self.clustering = clustering or JetClustering()

    @staticmethod
    def __scale_phi(phi: np.ndarray) -> np.ndarray:
        return ((phi + np.pi) % (2 * np.pi)) - np.pi # Scales phi to [-pi,pi]

    @staticmethod
    def __to_eta(theta: np.ndarray) -> np.ndarray:
        # Theta is in [0, pi] ; eta = -log(tan(theta/2))
        return -np.log(np.tan(theta / 2.0))

    @classmethod
    def __to_spherical_vec(cls, x: np.ndarray, y: np.ndarray, z: np.ndarray):
        """
        Vectorisation (spherical):
          r = sqrt(x^2 + y^2 + z^2)
          theta = atan2( sqrt(x^2+y^2), z )
          phi = piecewise(atan(y/x), +pi/-pi/pi/2/-pi/2/NAN)
          phi back in [-pi, pi]
          eta = -log(tan(theta/2))
        """
        x = x.astype(float, copy=False)
        y = y.astype(float, copy=False)
        z = z.astype(float, copy=False)

        r = np.sqrt(x * x + y * y + z * z)
        rho = np.sqrt(x * x + y * y)

        theta = np.arctan2(rho, z)

        phi = np.empty_like(x, dtype=float)

        phi.fill(np.nan) #Default is NaN

        # avoid 0/0
        nonzero_x = x != 0.0
        atan_yx = np.empty_like(x, dtype=float)
        atan_yx[nonzero_x] = np.arctan(y[nonzero_x] / x[nonzero_x])

        m1 = x > 0.0
        m2 = (x < 0.0) & (y >= 0.0)
        m3 = (x < 0.0) & (y < 0.0)
        m4 = (x == 0.0) & (y > 0.0)
        m5 = (x == 0.0) & (y < 0.0)

        phi[m1] = atan_yx[m1]
        phi[m2] = atan_yx[m2] + np.pi
        phi[m3] = atan_yx[m3] - np.pi
        phi[m4] = np.pi / 2.0
        phi[m5] = -np.pi / 2.0

        phi = cls.__scale_phi(phi)
        eta = cls.__to_eta(theta)
        return r, eta, phi


    @staticmethod
    def _group_by_event(df: pd.DataFrame) -> Dict[int, pd.DataFrame]:
        if df is None or df.empty:
            return {}
        return {int(k): v for k, v in df.groupby("eventNumber", sort=False)}

    @staticmethod
    def _event_weight(charged: pd.DataFrame, neutral: pd.DataFrame) -> float:
        has_c = charged is not None and not charged.empty and ("weight" in charged.columns)
        has_n = neutral is not None and not neutral.empty and ("weight" in neutral.columns)
        if not (has_c or has_n):
            return float("nan")

        parts = []
        if has_c:
            parts.append(charged["weight"])
        if has_n:
            parts.append(neutral["weight"])

        w = pd.concat(parts, ignore_index=True)
        if w.empty:
            return float("nan")
        uniq = pd.unique(w.to_numpy())
        return float(uniq[0])


    def build(
        self,
        event_numbers: Iterable[int],
        charged_final_states: pd.DataFrame,
        neutral_final_states: pd.DataFrame,
    ) -> pd.DataFrame:
        # Compact event indexes.  Unlike the previous implementation, these do
        # not retain one pandas DataFrame object per event.
        c_index = _EventRowIndex(charged_final_states)
        n_index = _EventRowIndex(neutral_final_states)

        # Buffers (same output order and schema as before).
        out_event   = []
        out_p       = []
        out_pt      = []
        out_px      = []
        out_py      = []
        out_pz      = []
        out_E       = []
        out_eta     = []
        out_phi     = []
        out_weight  = []

        for ev in event_numbers:
            ev = int(ev)
            c_positions = c_index.positions(ev)
            n_positions = n_index.positions(ev)

            has_c = c_positions.size != 0
            has_n = n_positions.size != 0
            if not has_c and not has_n:
                continue

            if not has_c:
                px = n_index.values(ev, "px", dtype=float)
                py = n_index.values(ev, "py", dtype=float)
                pz = n_index.values(ev, "pz", dtype=float)
                E  = n_index.values(ev, "E", dtype=float)
            elif not has_n:
                px = c_index.values(ev, "px", dtype=float)
                py = c_index.values(ev, "py", dtype=float)
                pz = c_index.values(ev, "pz", dtype=float)
                E  = c_index.values(ev, "E", dtype=float)
            else:
                # Charged rows followed by neutral rows is exactly the ordering
                # used by the historical implementation before clustering.
                px = np.concatenate([
                    c_index.values(ev, "px", dtype=float),
                    n_index.values(ev, "px", dtype=float),
                ])
                py = np.concatenate([
                    c_index.values(ev, "py", dtype=float),
                    n_index.values(ev, "py", dtype=float),
                ])
                pz = np.concatenate([
                    c_index.values(ev, "pz", dtype=float),
                    n_index.values(ev, "pz", dtype=float),
                ])
                E = np.concatenate([
                    c_index.values(ev, "E", dtype=float),
                    n_index.values(ev, "E", dtype=float),
                ])

            if px.size == 0:
                continue

            jets = self.clustering.cluster_event(px, py, pz, E)
            if len(jets) == 0:
                continue

            # Preserve the historical _event_weight semantics: if a charged
            # group has a weight column, its first value wins; otherwise use
            # the first neutral weight.  Missing weights remain NaN.
            if has_c and c_index.has_column("weight"):
                w = float(c_index.first_value(ev, "weight"))
            elif has_n and n_index.has_column("weight"):
                w = float(n_index.first_value(ev, "weight"))
            else:
                w = float("nan")

            # Keep the exact FastJet/Awkward result extraction used before.
            jpx = ak.to_numpy(jets["px"])
            jpy = ak.to_numpy(jets["py"])
            jpz = ak.to_numpy(jets["pz"])
            jE  = ak.to_numpy(jets["E"])

            _, jeta, jphi = self.__to_spherical_vec(jpx, jpy, jpz)

            jpt = _pt(jpx, jpy)
            jp = _p(jpx, jpy, jpz)

            out_event.extend([ev] * len(jets))
            out_p.extend(jp.tolist())
            out_pt.extend(jpt.tolist())
            out_px.extend(jpx.tolist())
            out_py.extend(jpy.tolist())
            out_pz.extend(jpz.tolist())
            out_E.extend(jE.tolist())
            out_eta.extend(jeta.tolist())
            out_phi.extend(jphi.tolist())
            out_weight.extend([w] * len(jets))

        return pd.DataFrame({
            "eventNumber": out_event,
            "p": out_p,
            "pt": out_pt,
            "px": out_px,
            "py": out_py,
            "pz": out_pz,
            "E": out_E,
            "eta": out_eta,
            "phi": out_phi,
            "weight": out_weight,
        })



def createJetDF(eventNumbers, chargedFinalStates, neutralFinalStates) -> pd.DataFrame:
    """Build a jet dataframe from charged and neutral final-state particles."""

    builder = JetDFBuilder()
    return builder.build(eventNumbers, chargedFinalStates, neutralFinalStates)
