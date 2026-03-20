from SetAnubis.core.Selection.domain.SelectionEngine import SelectionEngine, SelectionConfig, RunConfig, MinThresholds, MinDR
from SetAnubis.core.Selection.domain.DatasetSource import BundleIO
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

if __name__ == "__main__":
    df = pd.read_csv("db_paul.csv")
    SDFs_base = BundleIO.load_bundle("paul_dict.pkl.gz")

    cfs = SDFs_base["chargedFinalStates"].copy()
    nfs = SDFs_base["neutralFinalStates"].copy()

    cav = ATLASCavern()
    cav.createSimpleRPCs([cav.archRadius-0.2, cav.archRadius-0.6, cav.archRadius-1.2], RPCthickness=0.06)   # I added this line to create RPCs, otherwise intersectANUBISstationsSimple fails? This is consistent with ceiling configuration where in defineGeometry.py
                                                                                                            # line 1202 the simple RPCs are called ceiling (self.geoMode = "ceiling") and at then end in line 1365 in the __main__ section, this exact same call is in 
                                                                                                            # the if args.mode in ["", "simple"] block
    gcfg = GeometryBuildConfig(
        geo_cache_file="atlas_cavern.pkl",
        origin="IP",
        RPCeff=1.0,
        nRPCsPerLayer=1,
        geometryType=""  # "", "ceiling", "shaft", "shaft+cone", ...
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
    
    print(SDFs_base.keys())
    ev = np.unique(np.concatenate([
        cfs["eventNumber"].to_numpy(dtype=int, copy=False),
        nfs["eventNumber"].to_numpy(dtype=int, copy=False)
    ]))
    
    
    bundle = DataBundle.from_dict(SDFs_base)

    transform = ReweightDecayPositions(
        lifetime_s=1.0e-10,
        llp_pid=9900012,
        rng=RandomProvider(seed=42)
    )

    bundle2 = transform.apply(bundle)
    SDFs = bundle2.to_dict()
    # SDFs = SDFs_base

    SDFs["finalStatePromptJets"] = createJetDF(ev, cfs, nfs)
    
    # SDFs["LLPs"][["minDeltaR_Jets","minDeltaR_Tracks"]] = list(SDFs["LLPs"].apply(h.getMinDeltaR, args=(SDFs,selection), axis=1)) 
    
    iso = IsolationComputer(selection=sel_cfg)

    SDFs["LLPs"] = iso.attach_min_delta_r(SDFs)

    print(SDFs["LLPs"].columns)
    print(SDFs["LLPs"])
    

    runConfig = {
                 "reweightLifetime": not False, # Do not reweight the decay position of the LLP based on its lifetime.
                 "plotTrajectory": False, # Plot the trajectories of particles and whether there are any intersections with RPC layers.
    }


    

    run_cfg = RunConfig(runConfig["reweightLifetime"], runConfig["plotTrajectory"])
    engine = SelectionEngine()
    result = engine.apply_selection(SDFs, run_cfg, sel_cfg)

    print(result["cutFlow"])
    final_df = result["finalDF"]
