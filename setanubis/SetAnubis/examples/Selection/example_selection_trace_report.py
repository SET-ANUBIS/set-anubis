"""Capture every selection stage and export a JSON/HTML pass-fail report."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from SetAnubis.core.Geometry.adapters.ATLASCavernGeometry import (
    GeometryIntersections,
    GeometryRegion,
)
from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource
from SetAnubis.core.Selection.domain.SelectionEngine import (
    MinDR,
    RunConfig,
    SelectionConfig,
)
from SetAnubis.core.Selection.domain.SelectionPipeline import SelectionPipelineBuilder


class DemonstrationGeometry:
    """Deterministic geometry used to make each cut failure easy to inspect."""

    @property
    def default_decay_region(self) -> GeometryRegion:
        """Use the fiducial region for the first geometry cut."""
        return GeometryRegion.FIDUCIAL

    @property
    def default_fiducial_radius(self) -> float:
        """Return a nominal radius accepted by the demonstration geometry."""
        return 10.0

    def inside(
        self,
        region: GeometryRegion,
        decay_vertex_mm: Any,
        *,
        max_radius: float | None = None,
        tracking_only: bool = False,
    ) -> bool:
        """Interpret the synthetic vertex coordinates as pass/fail switches."""
        del max_radius, tracking_only
        x_position, detector_flag, _ = decay_vertex_mm
        if region is GeometryRegion.FIDUCIAL:
            return float(x_position) >= 0.0
        if region is GeometryRegion.DETECTOR:
            return bool(detector_flag)
        return True

    def intersections(
        self,
        row: pd.Series,
        decay_vertex_col: str,
        min_p_llp: float,
        plot_trajectory: bool = False,
    ) -> GeometryIntersections:
        """Return one hit for event 103 and two hits for the other events."""
        del decay_vertex_col, min_p_llp, plot_trajectory
        count = 1 if int(row["eventNumber"]) == 103 else 2
        return GeometryIntersections(
            points=[(float(index), 0.0, 0.0) for index in range(count)],
            station_indices=list(range(count)),
        )

    def filter_decay_hits(
        self,
        llps_df: pd.DataFrame,
        children_df: pd.DataFrame,
        nIntersections: int,
        nTracks: int,
        requireCharge: bool,
        prodVertex: str,
        decayVertex: str,
    ) -> pd.DataFrame:
        """Drop event 104 to demonstrate a tracker-stage failure."""
        del children_df, nIntersections, nTracks, requireCharge, prodVertex, decayVertex
        return llps_df[llps_df["eventNumber"] != 104]


def build_demo_bundle() -> dict[str, pd.DataFrame]:
    """Create candidates designed to fail at successive selection stages."""
    events = list(range(100, 108))
    llps = pd.DataFrame(
        {
            "eventNumber": events,
            "status": [1, 2, 2, 2, 2, 2, 2, 2],
            "weight": [1.0] * len(events),
            # Negative x fails the fiducial cut; y=1 marks a detector decay.
            "decayVertex": [
                (1.0, 0.0, 0.0),
                (-1.0, 0.0, 0.0),
                (1.0, 1.0, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
            ],
            "eta": [0.0] * len(events),
            "phi": [0.0] * len(events),
            # Event 105 fails MET; event 106 fails jet isolation.
            "MET": [50.0, 50.0, 50.0, 50.0, 50.0, 10.0, 50.0, 50.0],
            "minDeltaR_Jets": [0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.1, 0.8],
            "minDeltaR_Tracks": [0.8] * len(events),
        },
        index=[f"candidate-{event}" for event in events],
    )
    children = pd.DataFrame(
        columns=["eventNumber", "prodVertex", "decayVertex", "charge"]
    )
    return {"LLPs": llps, "LLPchildren": children}


def run_example(output_dir: str | Path) -> tuple[Path, Path]:
    """Run the synthetic selection and write matching JSON and HTML reports."""
    pipeline = (
        SelectionPipelineBuilder()
        .set_options(add_jets=False, compute_isolation=False)
        .build()
    )
    selection = SelectionConfig(
        geometry=DemonstrationGeometry(),
        minMET=30.0,
        minDR=MinDR(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
        nStations=2,
        nIntersections=2,
        nTracks=1,
    )
    result = pipeline.run(
        EventsBundleSource.from_bundle_dict(build_demo_bundle()),
        selection,
        RunConfig(capture_intermediate=True),
    )
    trace = result["trace"]

    print(trace.event_summary.to_string(index=False))
    return trace.write_report(
        output_dir,
        basename="selection_trace_demo",
        title="SET-ANUBIS selection trace demonstration",
    )


def main() -> None:
    """Parse the output directory and generate the demonstration reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="selection_trace_output",
        help="Directory receiving selection_trace_demo.json and .html",
    )
    args = parser.parse_args()
    json_path, html_path = run_example(args.output_dir)
    print(f"JSON report: {json_path}")
    print(f"HTML report: {html_path}")


if __name__ == "__main__":
    main()
