"""Build a reusable selection bundle from the packaged HNL event dataframe."""

from pathlib import Path

import pandas as pd

from SetAnubis.core.Selection.domain.DatasetSource import BundleIO
from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer

INPUT_DIR = Path(__file__).resolve().parent.parent / "InputFiles"
DF_FILE = INPUT_DIR / "hnl_df.csv"
BUNDLE_FILE = INPUT_DIR / "samples_dfs_hnl.pkl.gz"


if __name__ == "__main__":
    # Convert the flat event table into the dataframe groups expected by selection.
    dataframe = pd.read_csv(DF_FILE)
    analyzer = LLPAnalyzer(dataframe.copy(), pt_min_cfg={"chargedTrack": 0.5})
    bundle = analyzer.create_sample_dataframes(llpid=9900012)

    print(bundle["LLPs"])

    # BundleIO always writes gzip-compressed pickle data; the .gz suffix makes
    # that format visible to users and tools inspecting the generated file.
    BundleIO.save_bundle(bundle, BUNDLE_FILE)
    print(f"Saved selection bundle to {BUNDLE_FILE}")
