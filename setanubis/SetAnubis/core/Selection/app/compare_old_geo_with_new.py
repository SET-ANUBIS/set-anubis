from SetAnubis.core.Selection.domain.SelectionEngine import (
    SelectionEngine as SelectionEngineV1,
    SelectionConfig as SelectionConfigV1,
    RunConfig as RunConfigV1,
    MinThresholds as MinThresholdsV1,
    MinDR as MinDRV1,
)
from SetAnubis.core.Selection.domain.SelectionEnginev2 import (
    SelectionEngine as SelectionEngineV2,
    SelectionConfig as SelectionConfigV2,
    RunConfig as RunConfigV2,
    MinThresholds as MinThresholdsV2,
    MinDR as MinDRV2,
)

from SetAnubis.core.Selection.domain.DatasetSource import BundleIO
from SetAnubis.core.Selection.domain.JetBuilder import createJetDF
from SetAnubis.core.Selection.domain.ReweightTransformer import (
    DataBundle,
    ReweightDecayPositions,
    RandomProvider,
)
from SetAnubis.core.Selection.domain.isolation import IsolationComputer

# ancien chemin
from SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter import SelectionGeometryAdapter
from SetAnubis.core.Geometry.adapters.selection_adapter import GeometrySelectionAdapter
from SetAnubis.core.Geometry.domain.builder import GeometryBuilder, GeometryBuildConfig
from SetAnubis.core.Geometry.adapters.geometry_builder import CavernGeometryBuilder

# nouveau chemin
from SetAnubis.core.Geometry.adapters.ATLASCavernGeometry import (
    ATLASCavernGeometry,
    ATLASCavernGeometryConfig,
    ATLASCavernLayout,
    GeometryRegion,
)
from SetAnubis.core.Selection.adapters.input.ATLASCavernSelectionGeometryAdapter import (
    ATLASCavernSelectionGeometryAdapter,
)

import pandas as pd
import numpy as np


def build_common_sdfs():
    df = pd.read_csv("db_paul.csv")
    SDFs_base = BundleIO.load_bundle("paul_dict.pkl.gz")

    cfs = SDFs_base["chargedFinalStates"].copy()
    nfs = SDFs_base["neutralFinalStates"].copy()

    ev = np.unique(np.concatenate([
        cfs["eventNumber"].to_numpy(dtype=int, copy=False),
        nfs["eventNumber"].to_numpy(dtype=int, copy=False)
    ]))

    bundle = DataBundle.from_dict(SDFs_base)
    transform = ReweightDecayPositions(
        lifetime_s=1.0e-10,
        llp_pid=9900012,
        rng=RandomProvider(seed=42),
    )
    bundle2 = transform.apply(bundle)
    SDFs = bundle2.to_dict()

    SDFs["finalStatePromptJets"] = createJetDF(ev, cfs, nfs)
    return SDFs, SDFs_base


def build_old_selection():
    gcfg = GeometryBuildConfig(
        geo_cache_file="atlas_cavern.pkl",
        origin="IP",
        RPCeff=1.0,
        nRPCsPerLayer=1,
        geometryType="", 
    )
    builder = GeometryBuilder(CavernGeometryBuilder(gcfg))
    geom = builder.build()
    geom_adapter = GeometrySelectionAdapter(geom)
    sel_geo = SelectionGeometryAdapter(geom_adapter)

    sel_cfg = SelectionConfigV1(
        geometry=sel_geo,
        minMET=30.0,
        minP=MinThresholdsV1(LLP=0.1, chargedTrack=0.1, neutralTrack=0.1, jet=0.1),
        minPt=MinThresholdsV1(LLP=0.0, chargedTrack=5.0, neutralTrack=5.0, jet=15.0),
        minDR=MinDRV1(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
        nStations=2,
        nIntersections=2,
        nTracks=1,
    )
    return sel_cfg


    
def build_new_selection():
    base_cfg = ATLASCavernGeometryConfig(
        mode="ceiling",
        origin="IP",
        rpc_eff=1.0,
        n_rpcs_per_layer=1,
        use_cache=False,
        cache_file="atlas_cavern.pkl",
    )

    geometry = ATLASCavernGeometry.create(base_cfg)

    legacy_cfg = ATLASCavernGeometryConfig(
        mode="ceiling",
        origin="IP",
        rpc_eff=1.0,
        n_rpcs_per_layer=1,
        use_cache=False,
        cache_file="atlas_cavern.pkl",
        simple_rpc_radii=(
            geometry._cavern.archRadius - 0.2,
            geometry._cavern.archRadius - 1.2,
        ),
        simple_rpc_thickness=0.06,
        rpc_max_radius=geometry._cavern.archRadius - 1.2 - 0.5,
    )

    geometry.reconfigure(legacy_cfg)

    sel_geo = ATLASCavernSelectionGeometryAdapter(
        geometry,
        default_decay_region=GeometryRegion.FIDUCIAL,
    )

    sel_cfg = SelectionConfigV2(
        geometry=sel_geo,
        minMET=30.0,
        minP=MinThresholdsV2(LLP=0.1, chargedTrack=0.1, neutralTrack=0.1, jet=0.1),
        minPt=MinThresholdsV2(LLP=0.0, chargedTrack=5.0, neutralTrack=5.0, jet=15.0),
        minDR=MinDRV2(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
        nStations=2,
        nIntersections=2,
        nTracks=1,
    )
    return sel_cfg


def compare_cutflows(cf1, cf2):
    keys = sorted(set(cf1) | set(cf2))
    rows = []
    for k in keys:
        v1 = cf1.get(k, None)
        v2 = cf2.get(k, None)
        same = v1 == v2
        if isinstance(v1, float) or isinstance(v2, float):
            try:
                same = abs(float(v1) - float(v2)) < 1e-15
            except Exception:
                same = False
        rows.append((k, v1, v2, same))
    return pd.DataFrame(rows, columns=["key", "old", "new", "same"])


if __name__ == "__main__":
    SDFs, SDFs_base = build_common_sdfs()

    old_sel_cfg = build_old_selection()
    new_sel_cfg = build_new_selection()

    iso_old = IsolationComputer(selection=old_sel_cfg)
    SDFs_old = {k: v.copy() if hasattr(v, "copy") else v for k, v in SDFs.items()}
    SDFs_old["LLPs"] = iso_old.attach_min_delta_r(SDFs_old)

    iso_new = IsolationComputer(selection=new_sel_cfg)
    SDFs_new = {k: v.copy() if hasattr(v, "copy") else v for k, v in SDFs.items()}
    SDFs_new["LLPs"] = iso_new.attach_min_delta_r(SDFs_new)

    run_cfg_old = RunConfigV1(reweightLifetime=True, plotTrajectory=False)
    run_cfg_new = RunConfigV2(reweightLifetime=True, plotTrajectory=False)

    engine_old = SelectionEngineV1()
    engine_new = SelectionEngineV2()

    result_old = engine_old.apply_selection(SDFs_old, run_cfg_old, old_sel_cfg)
    result_new = engine_new.apply_selection(SDFs_new, run_cfg_new, new_sel_cfg)

    print("\n=== OLD cutFlow ===")
    print(result_old["cutFlow"])

    print("\n=== NEW cutFlow ===")
    print(result_new["cutFlow"])

    cmp_df = compare_cutflows(result_old["cutFlow"], result_new["cutFlow"])
    print("\n=== cutFlow comparison ===")
    print(cmp_df.to_string(index=False))

    old_idx = list(result_old["finalDF"].index)
    new_idx = list(result_new["finalDF"].index)

    print("\n=== final index comparison ===")
    print("same_final_indices =", old_idx == new_idx)
    print("old_final_indices  =", old_idx)
    print("new_final_indices  =", new_idx)

    common_cols = [
        c for c in [
            "eventNumber",
            "weight",
            "MET",
            "minDeltaR_Jets",
            "minDeltaR_Tracks",
            "intersectionStations",
            "intersectionsWithANUBIS",
        ]
        if c in result_old["finalDF"].columns and c in result_new["finalDF"].columns
    ]

    if common_cols:
        print("\n=== finalDF old ===")
        print(result_old["finalDF"][common_cols])

        print("\n=== finalDF new ===")
        print(result_new["finalDF"][common_cols])