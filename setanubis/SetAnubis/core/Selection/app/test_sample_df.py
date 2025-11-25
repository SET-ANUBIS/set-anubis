import time
from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer
import pandas as pd

if __name__ == "__main__":
    df = pd.read_csv("perfect_df.csv")
    LLPid = 9900012
    minPt = {"chargedTrack": 0.5}

    
    t1 = time.perf_counter()
    analyzer = LLPAnalyzer(df.copy(), pt_min_cfg=minPt)
    t2 = time.perf_counter()
    out_opt = analyzer.create_sample_dataframes(LLPid)
    t3 = time.perf_counter()
    
    print(out_opt["LLPs"])
    print("time creation: ", t2-t1)
    print("time func: ", t3-t2)