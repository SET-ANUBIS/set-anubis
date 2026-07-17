"""Run the current selection pipeline on a small packaged HNL sample."""

from importlib.resources import as_file, files

import pandas as pd

from SetAnubis.core.Geometry.adapters.ATLASCavernGeometry import ATLASCavernGeometry
from SetAnubis.core.Geometry.adapters.ATLASCavernGeometryConfig import (
    ATLASCavernGeometryConfig,
)
from SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter import (
    SelectionGeometryAdapter,
)
from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource
from SetAnubis.core.Selection.domain.SelectionEngine import (
    MinDR,
    MinThresholds,
    RunConfig,
    SelectionConfig,
)
from SetAnubis.core.Selection.domain.SelectionManager import SelectionManager
from SetAnubis.core.Selection.domain.SelectionPipeline import SelectionPipelineBuilder


def build_selection_geometry() -> SelectionGeometryAdapter:
    """Build the geometry backend required by the current selection engine."""
    geometry = ATLASCavernGeometry.create(
        ATLASCavernGeometryConfig(
            mode="ceiling",
            origin="IP",
            rpc_eff=1.0,
            n_rpcs_per_layer=1,
            use_cache=False,
        )
    )
    return SelectionGeometryAdapter(geometry)


def load_example_events(max_events: int = 5) -> pd.DataFrame:
    """Load a few events from the CSV shipped with the Python package."""
    resource = files("SetAnubis.examples.Selection").joinpath("InputFiles/hnl_df.csv")
    with as_file(resource) as csv_path:
        dataframe = pd.read_csv(csv_path)

    # Restrict the demonstration to a handful of complete events so it runs
    # quickly while still exercising bundle construction, jets and isolation.
    event_ids = dataframe["eventNumber"].drop_duplicates().head(max_events)
    return dataframe[dataframe["eventNumber"].isin(event_ids)].copy()


def main() -> None:
    """Execute the example and print the resulting cut flow."""
    selection = SelectionConfig(
        geometry=build_selection_geometry(),
        minMET=30.0,
        minP=MinThresholds(
            LLP=0.1, chargedTrack=0.1, neutralTrack=0.1, jet=0.1
        ),
        minPt=MinThresholds(
            LLP=0.0, chargedTrack=5.0, neutralTrack=5.0, jet=15.0
        ),
        minDR=MinDR(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
        nStations=2,
        nIntersections=2,
        nTracks=1,
    )

    pipeline = (
        SelectionPipelineBuilder()
        .set_options(
            add_jets=True,
            compute_isolation=True,
            selection_mode="standard",
        )
        .build()
    )
    source = EventsBundleSource.from_events_dataframe(load_example_events())
    combined = SelectionManager(pipeline).run_many(
        named_sources=[("packaged_hnl_sample", source)],
        sel_cfg=selection,
        run_cfg=RunConfig(reweightLifetime=False, plotTrajectory=False),
    )

    for sample in combined.per_sample:
        print(f"[{sample.name}] cutFlow: {sample.cutFlow}")
    print(f"Combined cut flow: {combined.cutflow_sum}")


if __name__ == "__main__":
    main()
