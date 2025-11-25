from SetAnubis.core.Selection.domain.SelectionEngine import SelectionEngine, SelectionConfig, RunConfig, MinThresholds, MinDR
from write_and_load_selection_dict import load_bundle
from SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter import SelectionGeometryAdapter
from SetAnubis.core.Geometry.adapters.selection_adapter import GeometrySelectionAdapter
from SetAnubis.core.Geometry.domain.defineGeometry import ATLASCavern
from SetAnubis.core.Selection.domain.JetBuilder import createJetDF
from SetAnubis.core.Selection.domain.ReweightTransformer import DataBundle, ReweightDecayPositions, RandomProvider
from SetAnubis.core.Selection.domain.isolation import IsolationComputer
from SetAnubis.core.Geometry.domain.builder import GeometryBuilder, GeometryBuildConfig
from SetAnubis.core.Geometry.adapters.geometry_builder import CavernGeometryBuilder
from SetAnubis.core.Geometry.adapters.geometry_query import CavernQuery

import pandas as pd
import numpy as np
import math
import time
from typing import Dict, Any, Tuple, Optional

def _find_col(df: pd.DataFrame, candidates) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None

def _ensure_eta_phi(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """Return (eta, phi) trying to use existing columns. Else calculate with px,py, pz."""
    eta_col = _find_col(df, ["eta", "Eta", "ETA"])
    phi_col = _find_col(df, ["phi", "Phi", "PHI"])
    if eta_col and phi_col:
        return df[eta_col].astype(float), df[phi_col].astype(float)

    px = _find_col(df, ["px", "Px", "PX"])
    py = _find_col(df, ["py", "Py", "PY"])
    pz = _find_col(df, ["pz", "Pz", "PZ"])
    if not (px and py and pz):
        raise ValueError("Impossible de déterminer (eta, phi) : colonnes manquantes.")
    pxv, pyv, pzv = df[px].astype(float).to_numpy(), df[py].astype(float).to_numpy(), df[pz].astype(float).to_numpy()
    phi = np.arctan2(pyv, pxv)
    p = np.sqrt(pxv**2 + pyv**2 + pzv**2)
    with np.errstate(divide="ignore", invalid="ignore"):
        eta = 0.5 * np.log((p + pzv) / (p - pzv))
    return pd.Series(eta, index=df.index), pd.Series(phi, index=df.index)

def _ensure_pt(df: pd.DataFrame) -> pd.Series:
    pt_col = _find_col(df, ["pt", "pT", "PT"])
    if pt_col:
        return df[pt_col].astype(float)
    # fallback
    px = _find_col(df, ["px", "Px", "PX"])
    py = _find_col(df, ["py", "Py", "PY"])
    if not (px and py):
        raise ValueError("Impossible de déterminer pT : colonnes (pt | pT | PT) ou (px, py) manquantes.")
    return np.sqrt(df[px].astype(float)**2 + df[py].astype(float)**2)

def _delta_r(eta1, phi1, eta2, phi2) -> np.ndarray:
    """ Return table of ΔR for every couples (1 x N2) by broadcast."""
    dphi = np.abs(phi1[:, None] - phi2[None, :])
    dphi = np.where(dphi > np.pi, 2*np.pi - dphi, dphi)
    deta = eta1[:, None] - eta2[None, :]
    return np.sqrt(deta**2 + dphi**2)

def legacy_attach_min_delta_r(SDFs: Dict[str, pd.DataFrame], sel_cfg: SelectionConfig) -> pd.DataFrame:
    LLPs  = SDFs["LLPs"].copy()
    jets  = SDFs["finalStatePromptJets"].copy()
    tracks = SDFs["chargedFinalStates"].copy()

    for df in (LLPs, jets, tracks):
        df.replace([np.inf, -np.inf], np.nan, inplace=True)

    jets_pt = _ensure_pt(jets)
    jets = jets.loc[jets_pt >= float(sel_cfg.minPt.jet)].copy()

    trk_pt = _ensure_pt(tracks)
    tracks = tracks.loc[trk_pt >= float(sel_cfg.minPt.chargedTrack)].copy()

    llp_eta, llp_phi = _ensure_eta_phi(LLPs)
    jet_eta, jet_phi = _ensure_eta_phi(jets)
    trk_eta, trk_phi = _ensure_eta_phi(tracks)

    ev_col = _find_col(LLPs, ["eventNumber", "event", "EventNumber", "Event"])
    if not ev_col:
        raise ValueError("Colonne d'événement absente dans LLPs.")
    ev_j = _find_col(jets, ["eventNumber", "event", "EventNumber", "Event"])
    ev_t = _find_col(tracks, ["eventNumber", "event", "EventNumber", "Event"])
    if not (ev_j and ev_t):
        raise ValueError("Colonne d'événement absente dans jets/tracks.")

    llp_index = LLPs.index
    n = len(LLPs)
    minDR_j = np.full(n, -1.0, dtype=float)
    minDR_t = np.full(n, -1.0, dtype=float)

    llp_groups  = LLPs.groupby(LLPs[ev_col])
    jets_groups = jets.groupby(jets[ev_j])
    trk_groups  = tracks.groupby(tracks[ev_t])

    for ev, llp_lab_index in llp_groups.groups.items():
        llp_lab = np.asarray(list(llp_lab_index))
        llp_pos = llp_index.get_indexer(llp_lab)
        if (llp_pos < 0).any():
            mask_ok = llp_pos >= 0
            llp_lab = llp_lab[mask_ok]
            llp_pos = llp_pos[mask_ok]
            if llp_pos.size == 0:
                continue

        llp_eta_ev = llp_eta.iloc[llp_pos].to_numpy()
        llp_phi_ev = llp_phi.iloc[llp_pos].to_numpy()
        valid_llp = np.isfinite(llp_eta_ev) & np.isfinite(llp_phi_ev)

        if ev in jets_groups.groups:
            j_lab = np.asarray(list(jets_groups.groups[ev]))
            if j_lab.size > 0:
                j_eta_ev = jet_eta.loc[j_lab].to_numpy()
                j_phi_ev = jet_phi.loc[j_lab].to_numpy()
                valid_j = np.isfinite(j_eta_ev) & np.isfinite(j_phi_ev)

                if valid_j.any() and valid_llp.any():
                    dR = _delta_r(llp_eta_ev[valid_llp], llp_phi_ev[valid_llp],
                                  j_eta_ev[valid_j],   j_phi_ev[valid_j])
                    minDR_j[llp_pos[valid_llp]] = np.min(dR, axis=1)

        if ev in trk_groups.groups:
            t_lab = np.asarray(list(trk_groups.groups[ev]))
            if t_lab.size > 0:
                t_eta_ev = trk_eta.loc[t_lab].to_numpy()
                t_phi_ev = trk_phi.loc[t_lab].to_numpy()
                valid_t = np.isfinite(t_eta_ev) & np.isfinite(t_phi_ev)

                if valid_t.any() and valid_llp.any():
                    dR = _delta_r(llp_eta_ev[valid_llp], llp_phi_ev[valid_llp],
                                  t_eta_ev[valid_t],   t_phi_ev[valid_t])
                    minDR_t[llp_pos[valid_llp]] = np.min(dR, axis=1)

    out = LLPs.copy()
    out["minDeltaR_Jets"] = minDR_j
    out["minDeltaR_Tracks"] = minDR_t
    return out

def selectIsolation(LLPs: pd.DataFrame, selection: Dict[str, Any]):
    LLPsIsoJets = LLPs[(LLPs.minDeltaR_Jets > selection["minDR"]["jet"]) | (LLPs.minDeltaR_Jets == -1)]
    cutFlow = {
        "nLLP_IsoJet": len(LLPsIsoJets.index),
        "nLLP_IsoJet_weighted": LLPsIsoJets["weight"].sum(),
    }
    cutIndices = {"nLLP_isoJet": LLPsIsoJets.index.tolist()}

    LLPsIsoCharged = LLPs[(LLPs.minDeltaR_Tracks > selection["minDR"]["chargedTrack"]) | (LLPs.minDeltaR_Tracks == -1)]
    cutFlow["nLLP_IsoCharged"] = len(LLPsIsoCharged.index)
    cutFlow["nLLP_IsoCharged_weighted"] = LLPsIsoCharged["weight"].sum()
    cutIndices["nLLP_isoCharged"] = LLPsIsoCharged.index.tolist()

    LLPsIsoAll = LLPsIsoJets[(LLPsIsoJets.minDeltaR_Tracks > selection["minDR"]["chargedTrack"]) | (LLPsIsoJets.minDeltaR_Tracks == -1)]
    cutFlow["nLLP_IsoAll"] = len(LLPsIsoAll.index)
    cutFlow["nLLP_IsoAll_weighted"] = LLPsIsoAll["weight"].sum()
    cutIndices["nLLP_isoAll"] = LLPsIsoAll.index.tolist()

    return {
        "dataframe": LLPsIsoAll,
        "cutFlow": cutFlow,
        "cutIndices": cutIndices,
        "additionalDataframes": {"IsoCharged": LLPsIsoCharged, "IsoJets": LLPsIsoJets},
    }

def compare_outputs(tag_a, out_a, tag_b, out_b) -> str:
    def _to_set(lst): return set(map(int, lst))
    rep = []
    for key in ["nLLP_IsoJet", "nLLP_IsoCharged", "nLLP_IsoAll"]:
        rep.append(f"{key}: {tag_a}={out_a['cutFlow'][key]} vs {tag_b}={out_b['cutFlow'][key]}")
    a_idx = _to_set(out_a["cutIndices"]["nLLP_isoAll"])
    b_idx = _to_set(out_b["cutIndices"]["nLLP_isoAll"])
    rep.append(f"Δ indices (IsoAll): only_in_{tag_a}={len(a_idx - b_idx)}, only_in_{tag_b}={len(b_idx - a_idx)}")
    for key in ["nLLP_IsoJet_weighted", "nLLP_IsoCharged_weighted", "nLLP_IsoAll_weighted"]:
        a = float(out_a["cutFlow"][key]); b = float(out_b["cutFlow"][key])
        rep.append(f"{key}: {tag_a}={a:.6g} vs {tag_b}={b:.6g} (Δ={a-b:.6g})")
    return "\n".join(rep)

def time_many(fn, *args, repeats=5, **kwargs):
    fn(*args, **kwargs)
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(*args, **kwargs)
        times.append(time.perf_counter() - t0)
    times = np.array(times)
    return float(np.median(times)), float(times.min())

if __name__ == "__main__":
    SDFs_base = load_bundle("paul_dict.pkl.gz")
    cfs = SDFs_base["chargedFinalStates"].copy()
    nfs = SDFs_base["neutralFinalStates"].copy()

    gcfg = GeometryBuildConfig(
        geo_cache_file="atlas_cavern.pkl",
        origin="IP",
        RPCeff=1.0,
        nRPCsPerLayer=1,
        geometryType="",
    )
    builder = GeometryBuilder(CavernGeometryBuilder(gcfg))
    geom: CavernQuery = builder.build()
    geom_adapter = GeometrySelectionAdapter(geom)
    sel_geo = SelectionGeometryAdapter(geom_adapter)

    sel_cfg = SelectionConfig(
        geometry=sel_geo,
        minMET=30.0,
        minP=MinThresholds(LLP=0.1, chargedTrack=0.1, neutralTrack=0.1, jet=0.1),
        minPt=MinThresholds(LLP=0.0, chargedTrack=5.0, neutralTrack=5.0, jet=15.0),
        minDR=MinDR(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
        nStations=2,
        nIntersections=2,
        nTracks=1,
    )

    ev = np.unique(np.concatenate([
        cfs["eventNumber"].to_numpy(dtype=int, copy=False),
        nfs["eventNumber"].to_numpy(dtype=int, copy=False),
    ]))
    SDFs = SDFs_base.copy()
    SDFs["finalStatePromptJets"] = createJetDF(ev, cfs, nfs)

    t_old_ms = None
    print("Calcul minΔR (baseline 'old' naïve)…")
    t0 = time.perf_counter()
    LLPs_old = legacy_attach_min_delta_r(SDFs, sel_cfg)
    t_old_ms = (time.perf_counter() - t0) * 1000.0

    iso = IsolationComputer(selection=sel_cfg)
    print("Calcul minΔR (nouveau attach_min_delta_r)…")
    t1 = time.perf_counter()
    LLPs_new = iso.attach_min_delta_r(SDFs.copy())
    t_new_ms = (time.perf_counter() - t1) * 1000.0

    med_old, best_old = time_many(legacy_attach_min_delta_r, SDFs, sel_cfg, repeats=7)
    med_new, best_new = time_many(iso.attach_min_delta_r, SDFs, repeats=7)

    n_llp = len(LLPs_new)
    print("\n=== Timings ===")
    print(f"OLD  legacy_attach_min_delta_r : {t_old_ms:.2f} ms  (médiane={med_old*1000:.2f} ms, min={best_old*1000:.2f} ms)  "
          f"~ {med_old/n_llp*1e6:.2f} µs/LLP (n={n_llp})")
    print(f"NEW  attach_min_delta_r        : {t_new_ms:.2f} ms  (médiane={med_new*1000:.2f} ms, min={best_new*1000:.2f} ms)  "
          f"~ {med_new/n_llp*1e6:.2f} µs/LLP (n={n_llp})")
    spd = med_old/med_new if med_new > 0 else float("inf")
    print(f"Speedup (OLD/NEW) ≈ ×{spd:.2f}")

    selection_dict = {
        "minDR": {"jet": float(sel_cfg.minDR.jet), "chargedTrack": float(sel_cfg.minDR.chargedTrack)}
    }
    out_old = selectIsolation(LLPs_old, selection_dict)
    out_new = selectIsolation(LLPs_new, selection_dict)

    print("\n=== Comparaison des sorties ===")
    print(compare_outputs("old", out_old, "new", out_new))

    iso_jet_old = set(out_old["cutIndices"]["nLLP_isoJet"])
    iso_all_old = set(out_old["cutIndices"]["nLLP_isoAll"])
    iso_jet_new = set(out_new["cutIndices"]["nLLP_isoJet"])
    iso_all_new = set(out_new["cutIndices"]["nLLP_isoAll"])
    assert iso_all_old.issubset(iso_jet_old), "OLD: IsoAll doit être sous-ensemble de IsoJet"
    assert iso_all_new.issubset(iso_jet_new), "NEW: IsoAll doit être sous-ensemble de IsoJet"

    only_old = sorted(list(iso_all_old - iso_all_new))
    only_new = sorted(list(iso_all_new - iso_all_old))
    if only_old or only_new:
        diff = pd.DataFrame({
            "only_in_old": pd.Series(only_old),
            "only_in_new": pd.Series(only_new),
        })
        diff.to_csv("delta_indices_isoAll_old_vs_new.csv", index=False)
        print("Désaccords indices IsoAll sauvegardés -> delta_indices_isoAll_old_vs_new.csv")
