"""Bridge the HepMC explorer to the canonical SET-ANUBIS selection pipeline."""

from __future__ import annotations

from typing import Any

from SetAnubis import SetAnubisInterface, ufo_path
from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource
from SetAnubis.core.Selection.domain.HepMCFrameBuilder import (
    HepmcFrameBuilder,
    HepmcFrameOptions,
)
from SetAnubis.core.Selection.domain.SelectionEngine import RunConfig
from SetAnubis.examples.Selection.compact_sample import (
    build_selection_config,
    build_selection_pipeline,
)

SELECTION_STAGE_ORDER = [
    "Original",
    "LLPDecay",
    "InCavern",
    "NotInATLAS",
    "Geometry",
    "Tracker",
    "MET",
    "IsoJets",
    "IsoCharged",
    "IsoAll",
    "Final",
]

SELECTION_STAGE_LABELS = {
    "Original": "Generated LLP candidates",
    "LLPDecay": "Decaying LLP candidates",
    "InCavern": "Decay in the ANUBIS fiducial region",
    "NotInATLAS": "Decay outside the ATLAS exclusion volume",
    "Geometry": "Trajectory intersects the detector geometry",
    "Tracker": "Charged-track multiplicity requirement",
    "MET": "Missing-transverse-momentum requirement",
    "IsoJets": "Jet-isolation requirement",
    "IsoCharged": "Charged-track isolation requirement",
    "IsoAll": "Combined isolation requirement",
    "Final": "Final selected candidates",
}


def standard_selection_description() -> dict[str, Any]:
    """Return the human-readable parameters used by the CPC benchmark."""
    config = build_selection_config()
    return {
        "geometry": "ANUBIS ceiling geometry, IP coordinate frame",
        "minimum_met_gev": float(config.minMET),
        "minimum_stations": int(config.nStations),
        "minimum_intersections": int(config.nIntersections),
        "minimum_tracks": int(config.nTracks),
        "minimum_jet_pt_gev": float(config.minPt.jet),
        "minimum_charged_track_pt_gev": float(config.minPt.chargedTrack),
        "isolation_delta_r": float(config.minDR.jet),
    }


def run_standard_hnl_selection(hepmc_path: str) -> dict[str, Any]:
    """Run the canonical HNL selection and return JSON-serialisable diagnostics."""
    try:
        import pyhepmc
    except ImportError as exc:  # pragma: no cover - optional dependency message
        raise RuntimeError(
            "Selection diagnostics require SetAnubis[selection] (pyhepmc)."
        ) from exc

    builder = HepmcFrameBuilder(
        neo_manager=SetAnubisInterface(ufo_path("UFO_HNL")),
        options=HepmcFrameOptions(progress_every=None, compute_met=False),
    )
    with pyhepmc.open(hepmc_path) as stream:
        dataframe, unknown_pids = builder.build_from_events(stream)

    result = build_selection_pipeline().run(
        EventsBundleSource.from_events_dataframe(dataframe),
        build_selection_config(),
        RunConfig(capture_intermediate=True),
    )
    trace = result["trace"]

    event_records = trace.event_summary.to_dict(orient="records")
    candidate_records = trace.candidate_summary.to_dict(orient="records")
    cut_flow = {
        str(key): float(value) if isinstance(value, float) else int(value)
        for key, value in result["cutFlow"].items()
    }
    return {
        "profile": "standard_hnl_cpc",
        "model": "UFO_HNL",
        "llp_pdg": 9900012,
        "input_events": int(dataframe["eventNumber"].nunique()),
        "input_rows": int(len(dataframe)),
        "unknown_pdg_ids": sorted(int(pid) for pid in unknown_pids),
        "cut_flow": cut_flow,
        "stage_order": SELECTION_STAGE_ORDER,
        "stage_labels": SELECTION_STAGE_LABELS,
        "events": event_records,
        "candidates": candidate_records,
        "configuration": standard_selection_description(),
    }
