from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Tuple, Any, List

import numpy as np
import pandas as pd

from SetAnubis.core.Selection.ports.input.ISelectionGeometry import ISelectionGeometry



def _vertex_col_in_df(df: pd.DataFrame, base: str, run_cfg: "RunConfig") -> str:
    if run_cfg.reweightLifetime and base in {"decayVertex", "prodVertex"}:
        weighted = f"{base}_weighted"
        return weighted if weighted in df.columns else base
    return base


def sel_check_in_cavern(row: pd.Series, geo: ISelectionGeometry, rpc_max_radius: float, decay_vertex_col: str) -> bool:
    return geo.in_cavern(row[decay_vertex_col], rpc_max_radius)


def sel_check_in_shaft(row: pd.Series, geo: ISelectionGeometry, rpc_max_radius: float, decay_vertex_col: str) -> bool:
    return geo.in_shaft(row[decay_vertex_col], rpc_max_radius)


def sel_check_in_atlas(row: pd.Series, geo: ISelectionGeometry, strict: bool, decay_vertex_col: str) -> bool:
    return geo.in_atlas(row[decay_vertex_col], strict)


def sel_check_llp_intersections(
    row: pd.Series,
    geo: ISelectionGeometry,
    decay_vertex_col: str,
    min_p_llp: float,
    plot_trajectory: bool = False,
) -> Tuple[List[Any], List[Any]]:
    """
    Return (intersectionsWithANUBIS, intersectionStations) for a given ligne of LLPs (row). Calculation si done by the Geometry part.
    """
    return geo.llp_intersections(row, decay_vertex_col, min_p_llp, plot_trajectory)


def sel_decay_hits(
    llps_df: pd.DataFrame,
    children_df: pd.DataFrame,
    geo: ISelectionGeometry,
    nIntersections: int,
    nTracks: int,
    requireCharge: bool,
    prodVertex: str,
    decayVertex: str,
) -> pd.DataFrame:
    """
    Ask Geometry for the calculation of of trackings hits.
    """
    return geo.decay_hits(
        llps_df,
        children_df,
        nIntersections=nIntersections,
        nTracks=nTracks,
        requireCharge=requireCharge,
        prodVertex=prodVertex,
        decayVertex=decayVertex,
    )

@dataclass(frozen=True)
class MinThresholds:
    LLP: float = 0.0
    chargedTrack: float = 5.0
    neutralTrack: float = 5.0
    jet: float = 15.0


@dataclass(frozen=True)
class MinDR:
    jet: float = 0.4
    chargedTrack: float = 0.4
    neutralTrack: float = 0.4


@dataclass(frozen=True)
class GeometryPort:
    geoMode: str
    RPCMaxRadius: float


@dataclass(frozen=True)
class SelectionConfig:
    geometry: GeometryPort
    minMET: float = 30.0
    minP: MinThresholds = field(default_factory=lambda: MinThresholds(LLP=0.1, chargedTrack=0.1, neutralTrack=0.1, jet=0.1))
    minPt: MinThresholds = field(default_factory=MinThresholds)
    minDR: MinDR = field(default_factory=MinDR)

    nStations: int = 2            # For intersection with ANUBIS
    nIntersections: int = 2       # FOr hits from desintegration product
    nTracks: int = 1              # Number of required tracks
    eachTrack: bool = False 
    RPCeff: float = 1.0           # RPC efficiency
    nRPCsPerLayer: int = 1


@dataclass(frozen=True)
class RunConfig:
    reweightLifetime: bool = False
    plotTrajectory: bool = False


class SelectionEngine:
    """
    Selection Pipeline, structure in multiple steps.
    
    Return {cutFlow, cutIndices, finalDF}
    """


    @staticmethod
    def _compute_min_delta_r_for_rows(
        rows: pd.DataFrame,
        SDFs: Dict[str, pd.DataFrame],
        selection: "SelectionConfig",
    ) -> pd.DataFrame:
        """
        Recompute minDeltaR_Jets and minDeltaR_Tracks for the given rows,
        using the same logic as the legacy helper.
        """
        jets_all   = SDFs.get("finalStatePromptJets", pd.DataFrame())
        tracks_all = SDFs.get("chargedFinalStates",   pd.DataFrame())

        # if we cannot compute anything, fill with -1 (legacy convention from Paul)
        if jets_all.empty and tracks_all.empty:
            out = rows.copy()
            out["minDeltaR_Jets"]   = -1.0
            out["minDeltaR_Tracks"] = -1.0
            return out

        def _delta_r_min_for_event(ev: int, eta0: float, phi0: float) -> tuple[float, float]:
            # select same-event jets/tracks
            j = jets_all[jets_all["eventNumber"] == ev] if not jets_all.empty else pd.DataFrame()
            t = tracks_all[tracks_all["eventNumber"] == ev] if not tracks_all.empty else pd.DataFrame()

            # apply kinematic thresholds
            if not j.empty:
                j = j[(j["pt"] > selection.minPt.jet) & (j["p"] > selection.minP.jet)]
            if not t.empty:
                t = t[(t["pt"] > selection.minPt.chargedTrack)]

            def _min_dr(df: pd.DataFrame) -> float:
                if df.empty:
                    return -1.0  # legacy “no object” convention from Paul
                d_eta = eta0 - df["eta"].to_numpy(dtype=float, copy=False)
                d_phi = phi0 - df["phi"].to_numpy(dtype=float, copy=False)
                dr = np.sqrt(d_eta * d_eta + d_phi * d_phi)
                return float(dr.min()) if dr.size else -1.0

            return _min_dr(j), _min_dr(t)

        jets_vals   = []
        tracks_vals = []
        # use itertuples for speed and safety
        for r in rows.itertuples(index=True):
            ev   = getattr(r, "eventNumber")
            eta0 = float(getattr(r, "eta"))
            phi0 = float(getattr(r, "phi"))
            drj, drt = _delta_r_min_for_event(ev, eta0, phi0)
            jets_vals.append(drj)
            tracks_vals.append(drt)

        out = rows.copy()
        out["minDeltaR_Jets"]   = jets_vals
        out["minDeltaR_Tracks"] = tracks_vals
        return out

    def apply_selection(
        self,
        SDFs: Dict[str, pd.DataFrame],
        run_config: RunConfig,
        selection: SelectionConfig,
    ) -> Dict[str, Any]:
        pd.options.mode.chained_assignment = None

        cut_flow: Dict[str, float | int] = {}
        cut_indices: Dict[str, List[int]] = {}

        llps = SDFs["LLPs"]
            
        
        cut_flow["nLLP_original"] = len(llps.index)
        cut_flow["nLLP_original_weighted"] = float(llps["weight"].sum() if "weight" in llps.columns else 0.0)

        # LLPs which decays
        step = self._select_decaying_llps(llps)
        cut_flow.update(step["cutFlow"]); cut_indices.update(step["cutIndices"])
        df = step["dataframe"]
        print("_select_decaying_llps", step["cutFlow"])
        
        # Geometry selection (cavern/shaft)
        geo_mode = (selection.geometry.geoMode or "").lower()
        if "shaft" in geo_mode:
            print("here")
            step = self._select_in_shaft(df, selection, run_config)
        elif (geo_mode == "") or ("ceiling" in geo_mode) or ("cavern" in geo_mode):
            print("or here")
            step = self._select_in_cavern(df, selection, run_config)
        else:
            raise ValueError(f"Unknown geometry mode: {selection.geometry.geoMode}")
        cut_flow.update(step["cutFlow"]); cut_indices.update(step["cutIndices"])
        df = step["dataframe"]
        print("_select_in_cavern ", step["cutFlow"])
        
        # OUtside ATLAS
        step = self._select_not_in_atlas(df, selection, run_config)
        cut_flow.update(step["cutFlow"]); cut_indices.update(step["cutIndices"])
        df = step["dataframe"]
        print("_select_not_in_atlas ", step["cutFlow"])
        
        # Intersections ANUBIS (RPC nStations)
        step = self._select_anubis_intersection(df, selection, run_config)
        cut_flow.update(step["cutFlow"]); cut_indices.update(step["cutIndices"])
        df = step["dataframe"]
        print("_select_anubis_intersection ", step["cutFlow"])
        
        # Tracking higs from desintegration product.
        step = self._select_tracks(df, SDFs["LLPchildren"], selection, run_config)
        cut_flow.update(step["cutFlow"]); cut_indices.update(step["cutIndices"])
        df = step["dataframe"]
        print("_select_tracks ", step["cutFlow"])
        
        # 6) Minimal MET
        step = self._select_met(df, selection)
        cut_flow.update(step["cutFlow"]); cut_indices.update(step["cutIndices"])
        df = step["dataframe"]
        print("_select_met : ", step["cutFlow"])
        
        # 7) Isolation
        step = self._select_isolation(df, selection, SDFs)
        cut_flow.update(step["cutFlow"]); cut_indices.update(step["cutIndices"])
        df = step["dataframe"]

        # Final
        cut_flow["nLLP_Final"] = len(df.index)
        cut_flow["nLLP_Final_weighted"] = float(df["weight"].sum() if "weight" in df.columns else 0.0)
        cut_indices["nLLP_Final"] = df.index.tolist()

        pd.options.mode.chained_assignment = "warn"
        return {"cutFlow": cut_flow, "cutIndices": cut_indices, "finalDF": df}

    #TODO : 2dv case
    def apply_selection_2dv(
        self,
        SDFs: Dict[str, pd.DataFrame],
        run_config: "RunConfig",
        selection: "SelectionConfig",
    ) -> Dict[str, Any]:
        """
        Mode 2DV (placeholder)
        """
        #Simple id, use same apply_selection with flags
        return self.apply_selection(SDFs, run_config, selection)

    @staticmethod
    def _vertex_col(base: str, run_config: RunConfig) -> str:
        """
        Choose weighted column if reweight is active (for decay and prod).
        """
        if run_config.reweightLifetime and base in {"decayVertex", "prodVertex"}:
            return f"{base}_weighted"
        return base


    @staticmethod
    def _select_decaying_llps(llps: pd.DataFrame) -> Dict[str, Any]:
        sel = llps[llps["status"] != 1]
        cutFlow = {
            "nLLP_LLPdecay": len(sel.index),
            "nLLP_LLPdecay_weighted": float(sel["weight"].sum() if "weight" in sel.columns else 0.0),
        }
        cutIndices = {"nLLP_LLPdecay": sel.index.tolist()}
        return {"dataframe": sel, "cutFlow": cutFlow, "cutIndices": cutIndices}

    @staticmethod
    def _apply_mask_and_pack(df: pd.DataFrame, mask: pd.Series, key: str) -> Dict[str, Any]:
        out = df[mask]
        return {
            "dataframe": out,
            "cutFlow": {f"nLLP_{key}": len(out.index), f"nLLP_{key}_weighted": float(out["weight"].sum() if "weight" in out.columns else 0.0)},
            "cutIndices": {f"nLLP_{key}": out.index.tolist()},
        }
        
    def _select_in_cavern(self, df: pd.DataFrame, selection: SelectionConfig, run_cfg: RunConfig) -> Dict[str, Any]:
        decay_col = _vertex_col_in_df(df, "decayVertex", run_cfg)
        mask = df.apply(
            sel_check_in_cavern,
            axis=1,
            args=(selection.geometry, selection.geometry.RPCMaxRadius, decay_col),
        )
        return self._apply_mask_and_pack(df, mask, "InCavern")


    def _select_in_shaft(self, df: pd.DataFrame, selection: SelectionConfig, run_cfg: RunConfig) -> Dict[str, Any]:
        decay_col = _vertex_col_in_df(df, "decayVertex", run_cfg)
        mask = df.apply(
            sel_check_in_shaft,
            axis=1,
            args=(selection.geometry, selection.geometry.RPCMaxRadius, decay_col),
        )
        return self._apply_mask_and_pack(df, mask, "InShaft")


    def _select_not_in_atlas(self, df: pd.DataFrame, selection: SelectionConfig, run_cfg: RunConfig) -> Dict[str, Any]:
        decay_col = _vertex_col_in_df(df, "decayVertex", run_cfg)
        mask = ~df.apply(
            sel_check_in_atlas,
            axis=1,
            args=(selection.geometry, True, decay_col),
        )
        return self._apply_mask_and_pack(df, mask, "NotInATLAS")


    def _select_anubis_intersection(self, df: pd.DataFrame, selection: SelectionConfig, run_cfg: RunConfig) -> Dict[str, Any]:
        decay_col = _vertex_col_in_df(df, "decayVertex", run_cfg)
        tmp = df.apply(
            sel_check_llp_intersections,
            axis=1,
            args=(selection.geometry, decay_col, selection.minP.LLP, run_cfg.plotTrajectory),
        )
        if len(tmp) != 0:
            df = df.copy()
            df[["intersectionsWithANUBIS", "intersectionStations"]] = pd.DataFrame(tmp.tolist(), index=tmp.index)
            n_needed = max(2, int(selection.nStations))
            mask = df.apply(lambda r: len(r["intersectionsWithANUBIS"]) >= n_needed, axis=1)
            out_df = df[mask]
        else:
            out_df = df

        cutFlow = {"nLLP_Geometry": len(out_df.index), "nLLP_Geometry_weighted": float(out_df["weight"].sum() if "weight" in out_df.columns else 0.0)}
        cutIndices = {"nLLP_Geometry": out_df.index.tolist()}
        return {"dataframe": out_df, "cutFlow": cutFlow, "cutIndices": cutIndices}


    def _select_tracks(
        self,
        df: pd.DataFrame,
        children: pd.DataFrame,
        selection: SelectionConfig,
        run_cfg: RunConfig,
    ) -> Dict[str, Any]:
        prod_col  = _vertex_col_in_df(children, "prodVertex", run_cfg)
        decay_col = _vertex_col_in_df(children, "decayVertex", run_cfg)

        # Use geometry as a row selector only
        selected = sel_decay_hits(
            df,
            children,
            selection.geometry,
            nIntersections=selection.nIntersections,
            nTracks=selection.nTracks,
            requireCharge=True,
            prodVertex=prod_col,
            decayVertex=decay_col,
        )

        # Whatever the adapter returns, derive the kept index from it…
        if isinstance(selected, pd.DataFrame):
            keep_idx = selected.index
        else:
            # be forgiving if an index-like is returned c:
            keep_idx = pd.Index(selected)

        # …and take rows from *df* to preserve all prior columns (e.g. minDeltaR_*).
        out = df.loc[keep_idx]

        cutFlow = {
            "nLLP_Tracker": len(out.index),
            "nLLP_Tracker_weighted": float(out["weight"].sum() if "weight" in out.columns else 0.0),
        }
        cutIndices = {"nLLP_Tracker": out.index.tolist()}
        return {"dataframe": out, "cutFlow": cutFlow, "cutIndices": cutIndices}

    @staticmethod
    def _ensure_met_column(df: pd.DataFrame) -> pd.DataFrame:
        """
        Guarantee a 'MET' column:
          - if already present -> return df unchanged
          - else if METx/METy present -> MET = sqrt(METx**2 + METy**2)
          - else -> MET = 0.0
        """
        if "MET" in df.columns:
            return df
        if ("METx" in df.columns) and ("METy" in df.columns):
            # avoid SettingWithCopy; return a new frame with MET computed
            met = np.sqrt(df["METx"].to_numpy(dtype=float, copy=False)**2 +
                          df["METy"].to_numpy(dtype=float, copy=False)**2)
            out = df.copy()
            out["MET"] = met
            return out
        # last resort (same than legacy): create a 0. MET column
        out = df.copy()
        out["MET"] = 0.0
        return out

    @staticmethod
    def _select_met(df: pd.DataFrame, selection: SelectionConfig) -> Dict[str, Any]:
        df2 = SelectionEngine._ensure_met_column(df)

        out = df2[df2["MET"] > selection.minMET]
        cutFlow = {
            "nLLP_MET": len(out.index),
            "nLLP_MET_weighted": float(out["weight"].sum() if "weight" in out.columns else 0.0),
        }
        cutIndices = {"nLLP_MET": out.index.tolist()}
        return {"dataframe": out, "cutFlow": cutFlow, "cutIndices": cutIndices}

    @staticmethod
    def _select_isolation(df: pd.DataFrame, selection: "SelectionConfig", SDFs: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        df2 = df.copy()

        have_df_cols = ("minDeltaR_Jets" in df2.columns) and ("minDeltaR_Tracks" in df2.columns)
        have_bundle  = ("LLPs" in SDFs and
                        ("minDeltaR_Jets" in SDFs["LLPs"].columns) and
                        ("minDeltaR_Tracks" in SDFs["LLPs"].columns))

        if have_df_cols:
            # USe what already in df (legacy from Paul: NaN -> -1)
            mdj = pd.to_numeric(df2["minDeltaR_Jets"],   errors="coerce")
            mdt = pd.to_numeric(df2["minDeltaR_Tracks"], errors="coerce")
        elif have_bundle:
            # Lookup by index from references LLPs
            base = SDFs["LLPs"]
            looked = base.reindex(df2.index)[["minDeltaR_Jets", "minDeltaR_Tracks"]]
            mdj = pd.to_numeric(looked["minDeltaR_Jets"],   errors="coerce")
            mdt = pd.to_numeric(looked["minDeltaR_Tracks"], errors="coerce")
        else:
            # Recalculation if needed
            from SetAnubis.core.Selection.domain.isolation import IsolationComputer
            iso = IsolationComputer(selection=selection)
            cols = iso.compute_for_llps(df2, SDFs)
            mdj = pd.to_numeric(cols["minDeltaR_Jets"],   errors="coerce")
            mdt = pd.to_numeric(cols["minDeltaR_Tracks"], errors="coerce")

        # Legacy from Paul : NaN/inf -> -1
        mdj = mdj.replace([np.inf, -np.inf], np.nan).fillna(-1.0).astype(float)
        mdt = mdt.replace([np.inf, -np.inf], np.nan).fillna(-1.0).astype(float)

        df2["minDeltaR_Jets"]   = mdj.to_numpy()
        df2["minDeltaR_Tracks"] = mdt.to_numpy()

        # cuts
        iso_jets = df2[(df2["minDeltaR_Jets"] > selection.minDR.jet) | (df2["minDeltaR_Jets"] == -1)]
        iso_ch   = df2[(df2["minDeltaR_Tracks"] > selection.minDR.chargedTrack) | (df2["minDeltaR_Tracks"] == -1)]
        iso_all  = iso_jets[(iso_jets["minDeltaR_Tracks"] > selection.minDR.chargedTrack) | (iso_jets["minDeltaR_Tracks"] == -1)]

        cutFlow = {
            "nLLP_IsoJet": len(iso_jets.index),
            "nLLP_IsoJet_weighted": float(iso_jets["weight"].sum() if "weight" in iso_jets.columns else 0.0),
            "nLLP_IsoCharged": len(iso_ch.index),
            "nLLP_IsoCharged_weighted": float(iso_ch["weight"].sum() if "weight" in iso_ch.columns else 0.0),
            "nLLP_IsoAll": len(iso_all.index),
            "nLLP_IsoAll_weighted": float(iso_all["weight"].sum() if "weight" in iso_all.columns else 0.0),
        }
        cutIndices = {
            "nLLP_isoJet": iso_jets.index.tolist(),
            "nLLP_isoCharged": iso_ch.index.tolist(),
            "nLLP_isoAll": iso_all.index.tolist(),
        }
        return {
            "dataframe": iso_all,
            "cutFlow": cutFlow,
            "cutIndices": cutIndices,
            "additionalDataframes": {"IsoCharged": iso_ch, "IsoJets": iso_jets},
        }
        