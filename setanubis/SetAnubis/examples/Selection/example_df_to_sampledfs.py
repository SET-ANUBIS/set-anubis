from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer
import pandas as pd

if __name__ == "__main__":
    df = pd.read_csv("perfect_df.csv")
    LLPid = 9900012
    minPt = {"chargedTrack": 0.5}

    analyzer = LLPAnalyzer(df.copy(), pt_min_cfg=minPt)
    out_opt = analyzer.create_sample_dataframes(LLPid)
    
    print(out_opt["LLPs"])
