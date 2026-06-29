from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer
from SetAnubis.core.Selection.domain.DatasetSource import BundleIO

import pandas as pd
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DF_FILE = os.path.join(CURRENT_DIR, "..","InputFiles", "hnl_df.csv")

if __name__ == "__main__":
    df = pd.read_csv(DF_FILE)
    LLPid = 9900012
    minPt = {"chargedTrack": 0.5}

    analyzer = LLPAnalyzer(df.copy(), pt_min_cfg=minPt)
    out_opt = analyzer.create_sample_dataframes(LLPid)
    
    print(out_opt["LLPs"])
    
    BundleIO().save_bundle(out_opt, "samples_dfs_hnl.pkl")
