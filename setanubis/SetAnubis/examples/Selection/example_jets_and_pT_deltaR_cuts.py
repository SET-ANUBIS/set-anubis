from SetAnubis.core.Selection.domain.SelectionEngine import SelectionConfig, MinThresholds, MinDR
from write_and_load_selection_dict import load_bundle
from SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter import SelectionGeometryAdapter
from SetAnubis.core.Geometry.adapters.selection_adapter import GeometrySelectionAdapter
from SetAnubis.core.Selection.domain.JetBuilder import createJetDF
from SetAnubis.core.Selection.domain.isolation import IsolationComputer
from SetAnubis.core.Geometry.domain.builder import GeometryBuilder, GeometryBuildConfig
from SetAnubis.core.Geometry.adapters.geometry_builder import CavernGeometryBuilder
from SetAnubis.core.Geometry.adapters.geometry_query import CavernQuery

import numpy as np



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

    iso = IsolationComputer(selection=sel_cfg)
    LLPs_new = iso.attach_min_delta_r(SDFs.copy())

    print(LLPs_new.head())

