"""
Benchmark: new SelectionEngine.apply_selection vs Paul legacy applySelection
Example
----------------
python benchmark_selection.py \
  --data-csv db_paul.csv \
  --bundle paul_dict.pkl.gz \
  --geo-cache atlas_cavern.pkl \
  --geo-mode "" -n 5 -w 1 --quiet-legacy
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import statistics as stats
import sys
import time
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd


def hrule(txt: str = "", ch: str = "─", width: int = 80):
    pad = max(0, width - len(txt) - 2)
    print(f"{ch*2} {txt} {ch*pad}")

def fmt_s(val: float) -> str:
    return f"{val:.6f}s"

def summary_stats(samples: List[float]) -> Dict[str, float]:
    return {
        "min": min(samples),
        "p25": float(np.percentile(samples, 25)),
        "median": stats.median(samples),
        "p75": float(np.percentile(samples, 75)),
        "max": max(samples),
        "mean": stats.mean(samples),
        "stdev": stats.pstdev(samples) if len(samples) > 1 else 0.0,
    }

def bench(func: Callable[[], Dict[str, Any]], warmups: int, iters: int) -> Tuple[List[float], Dict[str, Any]]:
    # Warm-up
    for _ in range(warmups):
        _ = func()
    # Timed
    times: List[float] = []
    last_res: Dict[str, Any] | None = None
    for _ in range(iters):
        t0 = time.perf_counter()
        last_res = func()
        t1 = time.perf_counter()
        times.append(t1 - t0)
    assert last_res is not None
    return times, last_res

def compare_cutflows(cf_new: Dict[str, float], cf_old: Dict[str, float]) -> pd.DataFrame:
    keys = sorted(set(cf_new) | set(cf_old))
    rows = []
    for k in keys:
        v_new = cf_new.get(k, np.nan)
        v_old = cf_old.get(k, np.nan)
        diff = (v_new - v_old) if (pd.notna(v_new) and pd.notna(v_old)) else np.nan
        rows.append((k, v_new, v_old, diff))
    return pd.DataFrame(rows, columns=["cut", "new", "old", "new-old"])

def compare_final_dfs(df_new: pd.DataFrame, df_old: pd.DataFrame, id_col: str | None = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    out["rows_new"] = int(len(df_new))
    out["rows_old"] = int(len(df_old))
    out["rows_diff"] = int(len(df_new) - len(df_old))
    if "weight" in df_new.columns and "weight" in df_old.columns:
        out["sumw_new"] = float(df_new["weight"].sum())
        out["sumw_old"] = float(df_old["weight"].sum())
        out["sumw_diff"] = float(out["sumw_new"] - out["sumw_old"])

    if id_col and id_col in df_new.columns and id_col in df_old.columns:
        idx_new = set(df_new[id_col].tolist())
        idx_old = set(df_old[id_col].tolist())
    else:
        idx_new = set(map(int, df_new.index.tolist())) if df_new.index.dtype.kind in "iu" else set(df_new.index.tolist())
        idx_old = set(map(int, df_old.index.tolist())) if df_old.index.dtype.kind in "iu" else set(df_old.index.tolist())
    inter = idx_new & idx_old
    only_new = list(idx_new - idx_old)
    only_old = list(idx_old - idx_new)
    out["overlap_count"] = int(len(inter))
    out["only_in_new_count"] = int(len(only_new))
    out["only_in_old_count"] = int(len(only_old))
    out["example_only_in_new"] = only_new[:10]
    out["example_only_in_old"] = only_old[:10]
    return out


def main():
    parser = argparse.ArgumentParser(description="Compare new SelectionEngine vs legacy applySelection")
    parser.add_argument("--data-csv", default="db_paul.csv", help="Path to db_paul.csv")
    parser.add_argument("--bundle", default="paul_dict.pkl.gz", help="Path to selection dict bundle (pkl or pkl.gz)")
    parser.add_argument("--geo-cache", default="atlas_cavern.pkl", help="Path to geometry cache file")
    parser.add_argument("--geo-mode", default="", help='Geometry mode: "", "ceiling", "shaft", "shaft+cone", ...')
    parser.add_argument("-n", "--iters", type=int, default=1, help="Timed iterations for each implementation")
    parser.add_argument("-w", "--warmups", type=int, default=1, help="Warm-up runs (not recorded)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--id-col", default=None, help="Optional ID column for finalDF overlap (defaults to index)")
    parser.add_argument("--json-out", default="benchmark_results.json", help="Where to write a JSON summary")
    parser.add_argument("--quiet-legacy", action="store_true", help="Silence legacy prints during run_old()")
    args = parser.parse_args()

    from SetAnubis.core.Selection.domain.SelectionEngine import (
        SelectionEngine, SelectionConfig, RunConfig, MinThresholds, MinDR
    )
    from write_and_load_selection_dict import load_bundle
    from SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter import SelectionGeometryAdapter
    from SetAnubis.core.Geometry.adapters.selection_adapter import GeometrySelectionAdapter
    from SetAnubis.core.Selection.domain.JetBuilder import createJetDF
    from SetAnubis.core.Selection.domain.ReweightTransformer import DataBundle, ReweightDecayPositions, RandomProvider
    from SetAnubis.core.Selection.domain.isolation import IsolationComputer
    from SetAnubis.core.Geometry.domain.builder import GeometryBuilder, GeometryBuildConfig
    from SetAnubis.core.Geometry.adapters.geometry_builder import CavernGeometryBuilder
    from SetAnubis.core.Geometry.adapters.geometry_query import CavernQuery

    from selectLLPs import applySelection as legacy_applySelection

    hrule("Loading data")
    _ = pd.read_csv(args.data_csv)

    # SDFs_base = load_bundle(args.bundle)

    SDFs_base = load_bundle("AfterSampleDataFrame_Run67.pickle")
    cfs = SDFs_base["chargedFinalStates"].copy()
    nfs = SDFs_base["neutralFinalStates"].copy()

    gcfg = GeometryBuildConfig(
        geo_cache_file=args.geo_cache,
        origin="IP",
        RPCeff=1.0,
        nRPCsPerLayer=1,
        geometryType=args.geo_mode,
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
    bundle = DataBundle.from_dict(SDFs_base)
    transform = ReweightDecayPositions(
        lifetime_s=1.0e-10,  # valeur arbitraire pour test
        llp_pid=9900012,     # idem
        rng=RandomProvider(seed=args.seed),
    )
    bundle2 = transform.apply(bundle)

    SDFs = bundle2.to_dict()
    SDFs["finalStatePromptJets"] = createJetDF(ev, cfs, nfs)

    iso = IsolationComputer(selection=sel_cfg)
    SDFs["LLPs"] = iso.attach_min_delta_r(SDFs)

    run_config_dict = {
        "reweightLifetime": True,
        "plotTrajectory": False,
    }
    run_cfg = RunConfig(run_config_dict["reweightLifetime"], run_config_dict["plotTrajectory"])

    legacy_geo = getattr(geom, "cavern", None) or getattr(geom, "cav", None)
    if legacy_geo is None:
        raise RuntimeError("CavernQuery n'expose pas d'ATLASCavern via .cavern/.cav")

    legacy_geo.RPCeff = gcfg.RPCeff
    legacy_geo.nRPCsPerLayer = gcfg.nRPCsPerLayer
    if not hasattr(legacy_geo, "geoMode") or not legacy_geo.geoMode:
        legacy_geo.geoMode = args.geo_mode

    def to_legacy_selection_dict(sel_cfg) -> Dict[str, Any]:
        return {
            "nStations": int(sel_cfg.nStations),
            "nIntersections": int(sel_cfg.nIntersections),
            "nTracks": int(sel_cfg.nTracks),
            "eachTrack": False,
            "RPCeff": gcfg.RPCeff,
            "nRPCsPerLayer": gcfg.nRPCsPerLayer,
            "minMET": float(sel_cfg.minMET),
            "minP": {
                "LLP": float(sel_cfg.minP.LLP),
                "chargedTrack": float(sel_cfg.minP.chargedTrack),
                "neutralTrack": float(sel_cfg.minP.neutralTrack),
                "jet": float(sel_cfg.minP.jet),
            },
            "minPt": {
                "LLP": float(sel_cfg.minPt.LLP),
                "chargedTrack": float(sel_cfg.minPt.chargedTrack),
                "neutralTrack": float(sel_cfg.minPt.neutralTrack),
                "jet": float(sel_cfg.minPt.jet),
            },
            "minDR": {
                "jet": float(sel_cfg.minDR.jet),
                "chargedTrack": float(sel_cfg.minDR.chargedTrack),
                "neutralTrack": float(sel_cfg.minDR.neutralTrack),
            },
            "geometry": legacy_geo,
        }

    selection_dict_legacy = to_legacy_selection_dict(sel_cfg)

    engine = SelectionEngine()

    def run_new():
        np.random.seed(args.seed)
        return engine.apply_selection(SDFs, run_cfg, sel_cfg)

    def run_old():
        np.random.seed(args.seed)
        if args.quiet_legacy:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                return legacy_applySelection(SDFs, run_config_dict, selection_dict_legacy)
        else:
            return legacy_applySelection(SDFs, run_config_dict, selection_dict_legacy)

    hrule("Benchmarking NEW (SelectionEngine.apply_selection)")
    times_new, res_new = bench(run_new, args.warmups, args.iters)
    s_new = summary_stats(times_new)
    print("runs:", args.iters, "| median:", fmt_s(s_new["median"]), "| mean:", fmt_s(s_new["mean"]))
    print("min/25%/50%/75%/max:", " / ".join(fmt_s(s_new[k]) for k in ["min","p25","median","p75","max"]))

    hrule("Benchmarking OLD (legacy applySelection)")
    times_old, res_old = bench(run_old, args.warmups, args.iters)
    s_old = summary_stats(times_old)
    print("runs:", args.iters, "| median:", fmt_s(s_old["median"]), "| mean:", fmt_s(s_old["mean"]))
    print("min/25%/50%/75%/max:", " / ".join(fmt_s(s_old[k]) for k in ["min","p25","median","p75","max"]))

    hrule("CutFlow comparison (new vs old)")
    cf_new = res_new["cutFlow"]
    cf_old = res_old["cutFlow"]
    df_cf = compare_cutflows(cf_new, cf_old)
    with pd.option_context("display.max_rows", None, "display.width", 160):
        print(df_cf.to_string(index=False))

    hrule("FinalDF comparison (shape/weights/overlap)")
    cmp_df = compare_final_dfs(res_new["finalDF"], res_old["finalDF"], id_col=args.id_col)
    for k, v in cmp_df.items():
        print(f"{k}: {v}")

    out = {
        "timing": {"new": s_new, "old": s_old, "samples_new": times_new, "samples_old": times_old},
        "cutflow_diff": df_cf.to_dict(orient="list"),
        "final_df_summary": cmp_df,
    }
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    hrule(f"Wrote {args.json_out} ✔")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n[ERROR]", type(e).__name__, str(e))
        sys.exit(1)
