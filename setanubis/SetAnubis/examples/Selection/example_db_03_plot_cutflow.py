"""Read the lightweight selection-results DB and plot one persisted cut flow."""

from __future__ import annotations

from pathlib import Path

from SetAnubis import SelectionResultsAccessor
from SetAnubis.examples._runtime import run_example_entrypoint

ROOT = Path("outputs/selection_db_demo")
RESULTS_DB = ROOT / "SelectionResults.db"
PLOT = ROOT / "cutflow.png"


def main() -> None:
    """Load the stored cuts into a DataFrame and save a simple cut-flow plot."""
    import matplotlib.pyplot as plt

    accessor = SelectionResultsAccessor(str(RESULTS_DB))
    frame = accessor.to_dataframe(analysis_name="baseline")
    print(frame.to_string(index=False))
    if frame.empty:
        raise SystemExit("No stored selection result found. Run example_db_02_select_and_store.py first.")

    cuts = [
        column
        for column in frame.columns
        if column.startswith("nLLP_") and not column.endswith("_weighted")
    ]
    values = frame.loc[frame.index[0], cuts].astype(float)

    PLOT.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 4))
    plt.bar(cuts, values)
    plt.xticks(rotation=60, ha="right")
    plt.ylabel("LLPs passing cut")
    plt.tight_layout()
    plt.savefig(PLOT)
    plt.close()
    print(f"Saved {PLOT}")


if __name__ == "__main__":
    results = SelectionResultsAccessor(str(RESULTS_DB))

    rows = results.query(
        model="SM_HeavyN_CKM_AllMasses_LO",
        campaign="compact_hnl_demo",
        scan_params={"VeN1": 1.0e-6},
        masses={9900012: 1.0},
        analysis_name="baseline",
    )
    raise SystemExit(run_example_entrypoint(main))

