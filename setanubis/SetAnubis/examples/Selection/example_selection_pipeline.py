from SetAnubis.core.Selection.domain.SelectionPipeline import SelectionPipelineBuilder, FileCache, IDataSource
from SetAnubis.core.Selection.domain.SelectionManager import SelectionManager, DatasetSpec
from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource, SourceConfig

from SetAnubis.core.Selection.domain.SelectionEngine import (
    SelectionEngine, SelectionConfig, RunConfig, MinThresholds, MinDR
)
from SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter import SelectionGeometryAdapter
from SetAnubis.core.Geometry.adapters.selection_adapter import GeometrySelectionAdapter
from SetAnubis.core.Geometry.domain.defineGeometry import ATLASCavern


from dataclasses import dataclass
import pandas as pd

@dataclass
class CSVDataSource(IDataSource):
    path: str
    name: str = "csv"

    def load_df(self) -> pd.DataFrame:
        return pd.read_csv(self.path)

    def dataset_id(self) -> str:
        return self.name


if __name__ == "__main__":

    cav = ATLASCavern()
    geom_adapter = GeometrySelectionAdapter(cav)
    sel_geo = SelectionGeometryAdapter(geom_adapter)

    sel_cfg = SelectionConfig(
        geometry=sel_geo,
        minMET=30.0,
        minP=MinThresholds(LLP=0.1, chargedTrack=0.1, neutralTrack=0.1, jet=0.1),
        minPt=MinThresholds(LLP=0.0, chargedTrack=5.0, neutralTrack=5.0, jet=15.0),
        minDR=MinDR(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
        nStations=2, nIntersections=2, nTracks=1,
    )

    run_cfg = RunConfig(reweightLifetime=False, plotTrajectory=False)

    builder = (
        SelectionPipelineBuilder()
        .set_options(add_jets=True, compute_isolation=True, selection_mode="standard")
        # .set_reweighter(lifetime_s=1.0e-10, llp_pid=9900012, seed=42)
        # .add_pre_df_transform(lambda df: df)
        # .add_post_bundle_transform(lambda b: b)
    )
    pipeline = builder.build()


    src_bundle = EventsBundleSource.from_bundle_file("paul_dict.pkl.gz")

    mgr = SelectionManager(pipeline)
    combined = mgr.run_many(
        named_sources=[("paul", src_bundle)],
        sel_cfg=sel_cfg,
        run_cfg=run_cfg,
    )

    for s in combined.per_sample:
        print(f"[{s.name}] cutFlow:", s.cutFlow)
    print("SUM:", combined.cutflow_sum)

    final_df = combined.per_sample[0].finalDF