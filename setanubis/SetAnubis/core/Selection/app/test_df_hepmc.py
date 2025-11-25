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

UFO_HNL_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "..", "..", "Assets", "UFO", "UFO_HNL"))

neo = SetAnubisInterface(UFO_HNL_DIR)

def on_progress(n: int):
    print(f"[build] {n} events")

builder = HepmcFrameBuilder(
    neo_manager=neo,
    options=HepmcFrameOptions(progress_every=200, compute_met=False),
    progress_hook=on_progress,
)

t0 = time.perf_counter()
with pyhepmc.open(HEPMC_FILE) as stream:
    df, unknown = builder.build_from_events(stream)
t1 = time.perf_counter()
builder_time = t1 - t0

df.to_csv("perfect_df_hahm.csv")
print(df.head(15))
print("Unknown PIDs:", unknown)

t2 = time.perf_counter()
df_old, old_part = createDFfromHEPMC(HEPMC_FILE)
t3 = time.perf_counter()
old_time = t3 - t2

print(df_old.head(15))
print("old particles : ", old_part)

def _fmt_s(x: float) -> str:
    # nice format (ms if <1s, else s)
    return f"{x*1e3:.1f} ms" if x < 1.0 else f"{x:.3f} s"

# acceleration factor
eps = 1e-12
if builder_time + old_time < eps:
    winner = "Égalité"
    speedup = 1.0
elif builder_time <= old_time:
    winner = "HepmcFrameBuilder"
    speedup = (old_time + eps) / max(builder_time, eps)
else:
    winner = "createDFfromHEPMC"
    speedup = (builder_time + eps) / max(old_time, eps)

print("\n=== Timing ===")
print(f"HepmcFrameBuilder      : {_fmt_s(builder_time)}")
print(f"createDFfromHEPMC      : {_fmt_s(old_time)}")
print(f"Gagnant                : {winner} ({speedup:.2f}× plus rapide)")
print("================\n")


def quick_df_compare(df_new, df_old, sort_keys=("eventNumber","particleIndex"), rtol=1e-6, atol=1e-12, sample=5):
    rep = {}
    rep["shape_new"], rep["shape_old"] = df_new.shape, df_old.shape

    cols_new, cols_old = list(df_new.columns), list(df_old.columns)
    rep["columns_same_and_order"] = (cols_new == cols_old)
    rep["cols_only_in_new"] = [c for c in cols_new if c not in cols_old]
    rep["cols_only_in_old"] = [c for c in cols_old if c not in cols_new]
    common = [c for c in cols_new if c in cols_old]
    rep["n_common_cols"] = len(common)

    rep["dtype_diff"] = {c: (df_new[c].dtype.name, df_old[c].dtype.name)
                         for c in common if df_new[c].dtype != df_old[c].dtype}

    # Align on common column
    A, B = df_new[common].copy(), df_old[common].copy()
    keys = [k for k in sort_keys if k in common]
    if keys:
        A = A.sort_values(keys).reset_index(drop=True)
        B = B.sort_values(keys).reset_index(drop=True)
    else:
        A = A.reset_index(drop=True); B = B.reset_index(drop=True)

    n = min(len(A), len(B))
    A, B = A.iloc[:n], B.iloc[:n]

    # num vs non-num
    num_cols = [c for c in common if np.issubdtype(A[c].dtype, np.number) and np.issubdtype(B[c].dtype, np.number)]
    cat_cols = [c for c in common if c not in num_cols]

    # numerical difference
    mism_num = {}
    for c in num_cols:
        bad = ~np.isclose(A[c].to_numpy(), B[c].to_numpy(), rtol=rtol, atol=atol, equal_nan=True)
        if bad.any():
            idxs = np.nonzero(bad)[0][:sample].tolist()
            mism_num[c] = {"count": int(bad.sum()),
                           "examples": [(int(i), A[c].iloc[i], B[c].iloc[i]) for i in idxs]}
    rep["numeric_mismatches"] = mism_num

    # categorical differences.
    mism_cat = {}
    for c in cat_cols:
        a, b = A[c].astype(str).to_numpy(), B[c].astype(str).to_numpy()
        bad = (a != b)
        if bad.any():
            idxs = np.nonzero(bad)[0][:sample].tolist()
            mism_cat[c] = {"count": int(bad.sum()),
                           "examples": [(int(i), A[c].iloc[i], B[c].iloc[i]) for i in idxs]}
    rep["categorical_mismatches"] = mism_cat

    rep["exact_equal_on_common"] = (not mism_num and not mism_cat and not rep["dtype_diff"] and A.shape == B.shape)
    return rep

report = quick_df_compare(df, df_old, sort_keys=("eventNumber","particleIndex"))
print(json.dumps(report, indent=2, default=str))

rtol, atol = 1e-6, 1e-12
assert "PID" in df.columns and "charge" in df.columns, "df doit contenir PID/charge"
assert "PID" in df_old.columns and "charge" in df_old.columns, "df_old doit contenir PID/charge"

common_cols = list(set(df.columns) & set(df_old.columns))
keys = [k for k in ("eventNumber","particleIndex") if k in common_cols]

A = df.sort_values(keys).reset_index(drop=True)
B = df_old.sort_values(keys).reset_index(drop=True)

# Charg mismatch
mismatch = ~np.isclose(A["charge"].to_numpy(), B["charge"].to_numpy(), rtol=rtol, atol=atol, equal_nan=True)
idx = np.nonzero(mismatch)[0]
print(f"Mismatches charge: {len(idx)} lignes")

M = pd.DataFrame({
    "eventNumber": A["eventNumber"].iloc[idx].to_numpy() if "eventNumber" in A else np.nan,
    "particleIndex": A["particleIndex"].iloc[idx].to_numpy() if "particleIndex" in A else np.nan,
    "PID": A["PID"].iloc[idx].to_numpy(),
    "charge_new": A["charge"].iloc[idx].to_numpy(),
    "charge_old": B["charge"].iloc[idx].to_numpy(),
})

# Classifier: flip sign or other.
M["abs_equal"] = np.isclose(np.abs(M["charge_new"]), np.abs(M["charge_old"]), rtol=rtol, atol=atol)
M["sign_flip"] = M["abs_equal"] & np.isclose(M["charge_new"], -M["charge_old"], rtol=rtol, atol=atol)
M["delta"] = M["charge_new"] - M["charge_old"]

print("\nBreakdown par type:")
print(M["sign_flip"].value_counts(dropna=False).rename({True:"sign_flip", False:"autre"}))

# Count by PID
top_pid = (M.groupby("PID").size().sort_values(ascending=False).head(20))
print("\nTop 20 PIDs causant des écarts:")
print(top_pid)

# Sample
sample_rows = M[M["PID"].isin(top_pid.index)].head(20)
print("\nÉchantillon (PID, eventNumber, particleIndex, new, old):")
print(sample_rows[["PID","eventNumber","particleIndex","charge_new","charge_old"]])

# Check pid
try:
    from particle import Particle
    def expected_charge(pid):
        try:
            return Particle.from_pdgid(int(pid)).charge
        except Exception:
            return np.nan
    M["charge_pdg"] = M["PID"].apply(expected_charge)

    M["new_matches_PDG"] = np.isclose(M["charge_new"], M["charge_pdg"], rtol=rtol, atol=atol, equal_nan=True)
    M["old_matches_PDG"] = np.isclose(M["charge_old"], M["charge_pdg"], rtol=rtol, atol=atol, equal_nan=True)
    pdg_check = pd.DataFrame({
        "new_ok": [M["new_matches_PDG"].sum(), len(M) - M["new_matches_PDG"].sum()],
        "old_ok": [M["old_matches_PDG"].sum(), len(M) - M["old_matches_PDG"].sum()],
    }, index=["matches","mismatches"])
    print("\nConformité PDG (sur les lignes en désaccord):")
    print(pdg_check)
except Exception as e:
    print("\n[Info] paquet 'particle' non disponible, saut de la vérification PDG.", e)

# save detail if needed
M.to_csv("charge_mismatches_detailed.csv", index=False)
print("\nFichier écrit: charge_mismatches_detailed.csv")
