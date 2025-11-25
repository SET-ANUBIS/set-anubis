from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd
import awkward as ak
import fastjet



def _pt(px: np.ndarray, py: np.ndarray) -> np.ndarray:
    return np.sqrt(px * px + py * py)

def _p(px: np.ndarray, py: np.ndarray, pz: np.ndarray) -> np.ndarray:
    return np.sqrt(px * px + py * py + pz * pz)


@dataclass(frozen=True)
class JetClusteringConfig:
    R: float = 0.4
    algorithm: int = fastjet.antikt_algorithm 


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
        return ((phi + np.pi) % (2 * np.pi)) - np.pi

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
        # Pre-group to avoid O(N) search for each events
        c_groups = self._group_by_event(charged_final_states)
        n_groups = self._group_by_event(neutral_final_states)

        # buffers (faster than append on DataFrame)
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
            cdf = c_groups.get(ev)
            ndf = n_groups.get(ev)

            if (cdf is None or cdf.empty) and (ndf is None or ndf.empty):
                continue

            if cdf is None or cdf.empty:
                px = ndf["px"].to_numpy(dtype=float, copy=False)
                py = ndf["py"].to_numpy(dtype=float, copy=False)
                pz = ndf["pz"].to_numpy(dtype=float, copy=False)
                E  = ndf["E" ].to_numpy(dtype=float, copy=False)
            elif ndf is None or ndf.empty:
                px = cdf["px"].to_numpy(dtype=float, copy=False)
                py = cdf["py"].to_numpy(dtype=float, copy=False)
                pz = cdf["pz"].to_numpy(dtype=float, copy=False)
                E  = cdf["E" ].to_numpy(dtype=float, copy=False)
            else:
                px = np.concatenate([
                    cdf["px"].to_numpy(dtype=float, copy=False),
                    ndf["px"].to_numpy(dtype=float, copy=False)
                ])
                py = np.concatenate([
                    cdf["py"].to_numpy(dtype=float, copy=False),
                    ndf["py"].to_numpy(dtype=float, copy=False)
                ])
                pz = np.concatenate([
                    cdf["pz"].to_numpy(dtype=float, copy=False),
                    ndf["pz"].to_numpy(dtype=float, copy=False)
                ])
                E  = np.concatenate([
                    cdf["E" ].to_numpy(dtype=float, copy=False),
                    ndf["E" ].to_numpy(dtype=float, copy=False)
                ])

            if px.size == 0:
                continue

            jets = self.clustering.cluster_event(px, py, pz, E)
            if len(jets) == 0:
                continue

            w = self._event_weight(cdf, ndf)

            jpx = np.fromiter((j.px for j in jets), count=len(jets), dtype=float)
            jpy = np.fromiter((j.py for j in jets), count=len(jets), dtype=float)
            jpz = np.fromiter((j.pz for j in jets), count=len(jets), dtype=float)
            jE  = np.fromiter((j.E  for j in jets), count=len(jets), dtype=float)

            _, jeta, jphi = self.__to_spherical_vec(jpx, jpy, jpz)

            jpt  = _pt(jpx, jpy)
            jp   = _p(jpx, jpy, jpz)

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

    builder = JetDFBuilder()
    return builder.build(eventNumbers, chargedFinalStates, neutralFinalStates)
