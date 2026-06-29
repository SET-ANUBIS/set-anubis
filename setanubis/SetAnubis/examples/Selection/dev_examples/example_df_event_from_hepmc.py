import os
import pyhepmc

from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.Selection.domain.HepMCFrameBuilder import HepmcFrameBuilder, HepmcFrameOptions
from SetAnubis.resources import ufo_path

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HEPMC_PATH = os.path.join(CURRENT_DIR, "..","InputFiles", "tag_1_pythia8_events.hepmc.gz")
OUTPUT_CSV_PATH = os.path.join(CURRENT_DIR, "..", "InputFiles", "hnl_df.csv")

if __name__ == "__main__":
    neo = SetAnubisInterface(ufo_path("UFO_HNL"))

    def on_progress(n: int):
        print(f"[build] {n} events")

    builder = HepmcFrameBuilder(
        neo_manager=neo,
        options=HepmcFrameOptions(progress_every=1, compute_met=False),
        progress_hook=on_progress,
    )

    with pyhepmc.open(HEPMC_PATH) as stream:
        df, unknown = builder.build_from_events(stream)
        
        df.to_csv(OUTPUT_CSV_PATH)