import ast
import numpy as np
import pandas as pd

def _parse_fourvec(v):
    if isinstance(v, tuple) and len(v) == 4:
        return v
    if isinstance(v, list) and len(v) == 4:
        return tuple(v)
    if isinstance(v, str):
        try:
            x = ast.literal_eval(v)
            if isinstance(x, (list, tuple)) and len(x) == 4:
                return tuple(x)
        except Exception:
            pass
    return v

def _flip_xy_vertex(v):
    v = _parse_fourvec(v)
    if not isinstance(v, (tuple, list)) or len(v) != 4:
        return v
    if tuple(v) == (-1, -1, -1, -1):
        return tuple(v)
    return (-float(v[0]), -float(v[1]), float(v[2]), float(v[3]))

def phi_fold_df(df: pd.DataFrame, llp_pid: int) -> pd.DataFrame:
    out = df.copy()

    llp_mask = (out["PID"].astype(int) == int(llp_pid)) & (out["phi"].astype(float) < 0.0)
    fold_events = set(out.loc[llp_mask, "eventNumber"].tolist())
    if not fold_events:
        return out

    mask = out["eventNumber"].isin(fold_events)

    out.loc[mask, "px"] = -out.loc[mask, "px"].to_numpy(dtype=float, copy=False)
    out.loc[mask, "py"] = -out.loc[mask, "py"].to_numpy(dtype=float, copy=False)

    phi = out.loc[mask, "phi"].to_numpy(dtype=float, copy=False)
    out.loc[mask, "phi"] = ((phi + np.pi) + np.pi) % (2 * np.pi) - np.pi

    for col in ("prodVertex", "decayVertex"):
        if col in out.columns:
            out.loc[mask, col] = out.loc[mask, col].map(_flip_xy_vertex)

    return out