from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Tuple, List, Dict, Any, Optional, Callable, Set
import math
import numpy as np
import pandas as pd

from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
Four = Tuple[float, float, float, float]


@dataclass(frozen=True)
class HepmcFrameOptions:
    """
        Options on the DataFrame creation
    """
    progress_every: Optional[int] = 100      # None -> No callback
    stop_after_events: Optional[int] = None  # safety limitation
    compute_met: bool = False                # if None, 0 everywhere


class HepmcFrameBuilder:
    """
    transform an iterable from pyhepmc to a Dataframe (ready for selection)

    ask NeoSetAnubis for any particle charge (using pdgid).
    Calculate the pT, phi, eta, etc.
    ctau = decayVertexDist / (gamma*beta).
    
     Return :
      (df, unknown_pids).
    """

    COLUMNS = [
        "eventNumber", "particleIndex",
        "px", "py", "pz", "pt", "E", "mass",
        "prodVertex", "prodVertexDist", "decayVertex", "decayVertexDist",
        "boost", "phi", "eta", "METx", "METy", "MET", "theta", "beta",
        "PID", "charge", "nParents", "nChildren", "parentIndices", "childrenIndices",
        "weight", "status", "ctau"
    ]

    def __init__(
        self,
        neo_manager : SetAnubisInterface,
        *,
        options: HepmcFrameOptions = HepmcFrameOptions(),
        progress_hook: Optional[Callable[[int], None]] = None,
    ) -> None:
        self.neo : SetAnubisInterface = neo_manager
        self.opt = options
        self.progress_hook = progress_hook


    def build_from_events(self, events: Iterable[Any]) -> Tuple[pd.DataFrame, List[int]]:
        """
        Args:
            events: Iterable of pyhepmc objects

        Returns:
            (df, unknown_pids)
        """
        hepMCdict: Dict[str, List[Any]] = {c: [] for c in self.COLUMNS}
        unknown_pids: Set[int] = set()

        event_number = 0
        for event in events:
            if self.opt.stop_after_events is not None and event_number >= self.opt.stop_after_events:
                break

            weight = self._get_event_weight(event)

            for p in event.particles:
                px, py, pz, E = self._get_momentum(p)
                pt = math.hypot(px, py)
                pabs = math.sqrt(px*px + py*py + pz*pz)

                mass = self._get_mass(p, E, pabs)

                phi = self._calculate_phi(px, py)
                theta = self._theta(px, py, pz, pabs)
                eta = self._eta(px, py, pz, pabs)

                beta = self._beta(pabs, E)
                gamma = self._gamma(beta)
                boost = self.calculate_boost(pabs, mass)
                prod_v, prod_r = self._get_vertex_tuple_and_len(getattr(p, "production_vertex", None))
                end_v, end_r = self._get_vertex_tuple_and_len(getattr(p, "end_vertex", None), missing=(-1, -1, -1, -1))

                parents, children = getattr(p, "parents", []), getattr(p, "children", [])
                parent_ids = [x.id for x in parents] if parents else []
                child_ids = [x.id for x in children] if children else []

                status = getattr(p, "status", None)
                pid = getattr(p, "pid", None)
                idx = getattr(p, "id", None)

                charge = self._get_charge_from_neo(pid, unknown_pids)

                ctau = self._safe_ctau(end_r, beta, gamma)

                hepMCdict["eventNumber"].append(event_number)
                hepMCdict["particleIndex"].append(idx)

                hepMCdict["px"].append(px)
                hepMCdict["py"].append(py)
                hepMCdict["pz"].append(pz)
                hepMCdict["pt"].append(pt)
                hepMCdict["E"].append(E)
                hepMCdict["mass"].append(mass)

                hepMCdict["prodVertex"].append(prod_v)
                hepMCdict["prodVertexDist"].append(prod_r)
                hepMCdict["decayVertex"].append(end_v)
                hepMCdict["decayVertexDist"].append(end_r)

                hepMCdict["phi"].append(phi)
                hepMCdict["eta"].append(eta)
                hepMCdict["theta"].append(theta)
                hepMCdict["beta"].append(beta)
                hepMCdict["boost"].append(boost)

                if self.opt.compute_met:
                    metx = mety = met = 0.0
                else:
                    metx = mety = met = 0.0
                hepMCdict["METx"].append(metx)
                hepMCdict["METy"].append(mety)
                hepMCdict["MET"].append(met)

                hepMCdict["PID"].append(pid)
                hepMCdict["charge"].append(charge)
                hepMCdict["nParents"].append(len(parents) if parents else 0)
                hepMCdict["nChildren"].append(len(children) if children else 0)
                hepMCdict["parentIndices"].append(parent_ids)
                hepMCdict["childrenIndices"].append(child_ids)

                hepMCdict["weight"].append(weight)
                hepMCdict["status"].append(status)
                hepMCdict["ctau"].append(ctau)

            event_number += 1
            if self.opt.progress_every and self.progress_hook and (event_number % self.opt.progress_every == 0):
                self.progress_hook(event_number)

        df = pd.DataFrame.from_dict(hepMCdict)

        for col in ("MET", "METx", "METy"):
            if col in df.columns:
                df[col] = df[col].astype(float)

        return df, sorted(unknown_pids)

    def _get_momentum(self, p: Any) -> Tuple[float, float, float, float]:
        mom = getattr(p, "momentum", None)
        if mom is None:
            #If None -> (0,0,0)
            return (0.0, 0.0, 0.0, 0.0)

        return (float(mom[0]), float(mom[1]), float(mom[2]), float(mom[3]))

    def _get_mass(self, p: Any, E: float, pabs: float) -> float:
        # If Generated mass
        m = getattr(p, "generated_mass", None)
        if m is not None:
            return float(m)
        
        # fallback: m^2 = E^2 - |p|^2
        m2 = E*E - pabs*pabs
        return math.sqrt(m2) if m2 > 0 else 0.0

    def _theta(self, px: float, py: float, pz: float, pabs: float) -> float:
        return math.acos(pz / pabs) if pabs != 0.0 else 0.0

    def _eta(self, px: float, py: float, pz: float, pabs: float) -> float:
        mom = np.sqrt(np.power(px,2) + np.power(py,2) + np.power(pz,2))

        if mom-pz==0 or mom+pz==0:
            eta = np.nan
        else:
            eta = 0.5*np.log( (mom + pz) / (mom - pz))
        
        # To avoid divergences impose a large value of eta cutoff, effectively longitudinal at eta=1E6
        if (eta > 1E9):
            return 1E9
        elif (eta < -1E9):
            return -1E9
        elif (np.isnan(eta)):
            return np.sign(pz)*np.nan_to_num(eta, nan=1E9) # undefined when longitudinal, then direction of pz gives the direction
        else:
            return eta

    def _beta(self, pabs: float, E: float) -> float:
        if E <= 0.0:
            return 0.0
        b = pabs / E
        return min(max(b, 0.0), 0.999999999999)  # avoid beta =1.0 exact

    def _gamma(self, beta: float) -> float:
        if beta <= 0.0:
            return 1.0
        inv = 1.0 - beta*beta
        return 1.0 / math.sqrt(inv) if inv > 0.0 else float("inf")

    def calculate_boost(self, p, m):
        # E=gamma*mc^2, so if m is in GeV and so is E then gamma = E/m
        e = np.sqrt(p * p + m * m)
        if m==0:
            return np.nan # massless particles have an undefined boost
        return e / m

    def _calculate_phi(self, px, py):
        phi = np.arctan2(py, px)
        if np.isclose(phi, -np.pi):
            phi = np.pi

        return phi

    def _get_vertex_tuple_and_len(self, vtx: Any, *, missing: Four = (0.0, 0.0, 0.0, 0.0)) -> Tuple[Four, float]:
        """
            Return ((x,y,z,t), r) or r = sqrt(x^2+y^2+z^2).
            If vtx is None, return missing and 0.0
            Si vtx est None, on renvoie missing et 0.0.
        """
        if vtx is None or getattr(vtx, "position", None) is None:
            return missing, 0.0
        pos = vtx.position
        x, y, z, t = float(pos.x), float(pos.y), float(pos.z), float(pos.t)
        r = math.sqrt(x*x + y*y + z*z)
        return (x, y, z, t), r

    def _safe_ctau(self, decay_r: float, beta: float, gamma: float) -> float:
        denom = gamma * beta
        if denom <= 0.0 or not math.isfinite(denom):
            return 0.0
        return decay_r / denom

    def _get_event_weight(self, event: Any) -> float:
        # pyhepmc v2/3 compatible (event.weight() or event.weights())
        w = None
        if hasattr(event, "weight") and callable(getattr(event, "weight")):
            try:
                w = float(event.weight())
            except Exception:
                w = None
        if w is None and hasattr(event, "weights"):
            ws = event.weights() if callable(event.weights) else event.weights
            try:
                if isinstance(ws, (list, tuple)) and ws:
                    w = float(ws[0])
            except Exception:
                w = None
        return w if w is not None else 1.0

    def _get_charge_from_neo(self, pid: Optional[int], unknown_pids: Set[int]) -> Optional[float]:
        info = self.neo.get_particle(pid) if hasattr(self.neo, "get_particle") else self.neo.get_particle_info(pid)
        if pid is None:
            return None
        try:
            info = self.neo.get_particle(pid) if hasattr(self.neo, "get_particle") else self.neo.get_particle_info(pid)
        except Exception:
            info = None
        if isinstance(info, dict) and "charge" in info:
            ch = info["charge"]
            try:
                return float(ch)
            except Exception:
                return None
        unknown_pids.add(int(pid))
        return None
