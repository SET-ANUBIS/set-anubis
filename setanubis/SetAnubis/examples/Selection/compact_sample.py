"""Shared loaders and configuration for the compact real-event HNL sample."""

from __future__ import annotations

import json
from importlib.resources import as_file, files
from typing import Any

import pandas as pd

from SetAnubis.core.Geometry.adapters.ATLASCavernGeometry import ATLASCavernGeometry
from SetAnubis.core.Geometry.adapters.ATLASCavernGeometryConfig import (
    ATLASCavernGeometryConfig,
)
from SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter import (
    SelectionGeometryAdapter,
)
from SetAnubis.core.Selection.domain.DatasetSource import BundleIO
from SetAnubis.core.Selection.domain.SelectionEngine import (
    MinDR,
    MinThresholds,
    SelectionConfig,
)
from SetAnubis.core.Selection.domain.SelectionPipeline import (
    SelectionPipeline,
    SelectionPipelineBuilder,
)

_INPUT_DIR = "InputFiles"
_DATAFRAME_NAME = "hnl_selection_cutflow_df.csv.gz"
_BUNDLE_NAME = "hnl_selection_cutflow_bundle.pkl.gz"
_MANIFEST_NAME = "hnl_selection_cutflow_manifest.json"
_HEPMC_NAME = "hnl_selection_cutflow.hepmc.gz"


def input_resource(name: str):
    """Return a traversable resource from the packaged selection input directory."""
    return files("SetAnubis.examples.Selection").joinpath(_INPUT_DIR, name)


def load_compact_dataframe() -> pd.DataFrame:
    """Load the seven-event flat dataframe from the packaged gzip CSV."""
    with as_file(input_resource(_DATAFRAME_NAME)) as path:
        return pd.read_csv(path)


def load_compact_bundle() -> dict[str, pd.DataFrame]:
    """Load the trusted gzip-pickle bundle derived from the compact sample."""
    with as_file(input_resource(_BUNDLE_NAME)) as path:
        return BundleIO.load_bundle(path)


def load_compact_manifest() -> dict[str, Any]:
    """Load provenance and expected cut outcomes for the seven events."""
    return json.loads(input_resource(_MANIFEST_NAME).read_text(encoding="utf-8"))


def compact_hepmc_resource():
    """Return the packaged HepMC2 source containing the seven real events."""
    return input_resource(_HEPMC_NAME)


def build_selection_config() -> SelectionConfig:
    """Build the standard geometry and cuts used to classify the compact sample."""
    geometry = ATLASCavernGeometry.create(
        ATLASCavernGeometryConfig(
            mode="ceiling",
            origin="IP",
            rpc_eff=1.0,
            n_rpcs_per_layer=1,
            use_cache=False,
        )
    )
    return SelectionConfig(
        geometry=SelectionGeometryAdapter(geometry),
        minMET=30.0,
        minP=MinThresholds(
            LLP=0.1,
            chargedTrack=0.1,
            neutralTrack=0.1,
            jet=0.1,
        ),
        minPt=MinThresholds(
            LLP=0.0,
            chargedTrack=5.0,
            neutralTrack=5.0,
            jet=15.0,
        ),
        minDR=MinDR(jet=0.4, chargedTrack=0.4, neutralTrack=0.4),
        nStations=2,
        nIntersections=2,
        nTracks=1,
    )


def build_selection_pipeline() -> SelectionPipeline:
    """Build the standard pipeline with prompt jets and isolation enabled."""
    return (
        SelectionPipelineBuilder()
        .set_options(
            add_jets=True,
            compute_isolation=True,
            selection_mode="standard",
        )
        .build()
    )
