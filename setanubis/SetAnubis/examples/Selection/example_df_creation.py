import json
import time
import numpy as np
import pandas as pd
import pyhepmc

from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.Selection.domain.HepMCFrameBuilder import HepmcFrameBuilder, HepmcFrameOptions
from selectLLPs import createDFfromHEPMC

HEPMC_FILE = (
    "db/Temp/madgraph/Events/Events/run_01_decayed_1/"
    "tag_1_pythia8_events.hepmc/tag_1_pythia8_events.hepmc"
)

HEPMC_FILE = (
    "tag_1_pythia8_events.hepmc"
)

import os

UFO_HNL_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "..", "Assets", "UFO", "UFO_HNL"))

if __name__ == "__main__":
    neo = SetAnubisInterface(UFO_HNL_DIR)

    def on_progress(n: int):
        print(f"[build] {n} events")

    builder = HepmcFrameBuilder(
        neo_manager=neo,
        options=HepmcFrameOptions(progress_every=200, compute_met=False),
        progress_hook=on_progress,
    )

    with pyhepmc.open(HEPMC_FILE) as stream:
        df, unknown = builder.build_from_events(stream)
