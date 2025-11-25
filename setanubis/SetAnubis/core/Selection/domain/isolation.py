from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple
import numpy as np
import pandas as pd
from SetAnubis.core.Selection.domain.SelectionEngine import SelectionConfig, MinThresholds


def _wrap_delta_phi(dphi: np.ndarray) -> np.ndarray:
    """Replie Δφ sur [-π, π]."""
    return (dphi + np.pi) % (2.0 * np.pi) - np.pi

@dataclass
class IsolationComputer:
    """
    Calculation of min ΔR for each LLP and (jets, charged tracks) of each events.
    - Jets   : pt > minPt.jet AND p > minP.jet
    - Tracks : pt > minPt.chargedTrack
    If an even doesn't contain any object of a given type, minΔR = -1.
    """
    selection: "SelectionConfig"

    def _prepare_event_maps(
        self,
        jets: pd.DataFrame,
        tracks: pd.DataFrame,
    ) -> Tuple[Dict[int, Tuple[np.ndarray, np.ndarray]],
               Dict[int, Tuple[np.ndarray, np.ndarray]]]:
        """
        eventNumber → maps:
          jets_map[event]   = (eta_jets, phi_jets)
          tracks_map[event] = (eta_tracks, phi_tracks)
        """

        if not jets.empty:
            j = jets[
                (jets["pt"].to_numpy() > float(self.selection.minPt.jet)) &
                (jets["p"].to_numpy()  > float(self.selection.minP.jet))
            ][["eventNumber", "eta", "phi"]]
        else:
            j = jets

        if not tracks.empty:
            t = tracks[
                (tracks["pt"].to_numpy() > float(self.selection.minPt.chargedTrack))
            ][["eventNumber", "eta", "phi"]]
        else:
            t = tracks

        jets_map: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
        tracks_map: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}

        if not j.empty:
            for ev, g in j.groupby("eventNumber", sort=False):
                jets_map[int(ev)] = (
                    g["eta"].to_numpy(dtype=float, copy=False),
                    g["phi"].to_numpy(dtype=float, copy=False),
                )

        if not t.empty:
            for ev, g in t.groupby("eventNumber", sort=False):
                tracks_map[int(ev)] = (
                    g["eta"].to_numpy(dtype=float, copy=False),
                    g["phi"].to_numpy(dtype=float, copy=False),
                )

        return jets_map, tracks_map

    @staticmethod
    def _min_delta_r_to_set(eta0: float, phi0: float,
                            etas: np.ndarray, phis: np.ndarray) -> float:
        """
        Min ΔR between (eta0, phi0) and object scatter (etas, phis).
        Return -1 if empty set.
        """
        if etas.size == 0:
            return -1.0
        dEta = etas - eta0
        dPhi = _wrap_delta_phi(phis - phi0)
        dR2  = dEta * dEta + dPhi * dPhi

        m = np.nanmin(dR2)
        return float(np.sqrt(m)) if np.isfinite(m) else -1.0

    def compute_for_llps(
        self,
        llps: pd.DataFrame,
        sample_dfs: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """
        Calculation of minDeltaR_Jets and minDeltaR_Tracks columns for every LLPs.
        
        need to have finalStatePromptJets (jets prompt) and chargedFinalStates (charged tracks) in sample_dfs.
        """
        jets = sample_dfs.get("finalStatePromptJets", pd.DataFrame())
        tracks = sample_dfs.get("chargedFinalStates", pd.DataFrame())

        jets_map, tracks_map = self._prepare_event_maps(jets, tracks)

        out_min_dR_j = np.empty(len(llps), dtype=float)
        out_min_dR_t = np.empty(len(llps), dtype=float)

        ev_arr  = llps["eventNumber"].to_numpy(copy=False)
        eta_arr = llps["eta"].to_numpy(dtype=float, copy=False)
        phi_arr = llps["phi"].to_numpy(dtype=float, copy=False)

        for i in range(len(llps)):
            ev = int(ev_arr[i])
            eta0 = float(eta_arr[i])
            phi0 = float(phi_arr[i])

            if ev in jets_map:
                etas_j, phis_j = jets_map[ev]
                out_min_dR_j[i] = self._min_delta_r_to_set(eta0, phi0, etas_j, phis_j)
            else:
                out_min_dR_j[i] = -1.0

            if ev in tracks_map:
                etas_t, phis_t = tracks_map[ev]
                out_min_dR_t[i] = self._min_delta_r_to_set(eta0, phi0, etas_t, phis_t)
            else:
                out_min_dR_t[i] = -1.0

        return pd.DataFrame({
            "minDeltaR_Jets": out_min_dR_j,
            "minDeltaR_Tracks": out_min_dR_t,
        })

    def attach_min_delta_r(
        self,
        sdf_bundle: Dict[str, pd.DataFrame],
        llp_key: str = "LLPs",
    ) -> pd.DataFrame:
        """
        Add columns to LLPs dataframe in the SDFs bundle and returns it.
        """
        llps = sdf_bundle[llp_key]
        cols = self.compute_for_llps(llps, sdf_bundle)
        sdf_bundle[llp_key] = llps.assign(
            minDeltaR_Jets=cols["minDeltaR_Jets"].to_numpy(),
            minDeltaR_Tracks=cols["minDeltaR_Tracks"].to_numpy(),
        )
        return sdf_bundle[llp_key]
