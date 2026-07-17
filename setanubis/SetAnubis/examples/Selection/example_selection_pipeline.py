"""Run the standard selection on seven compact real HNL events."""

from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource
from SetAnubis.core.Selection.domain.SelectionEngine import RunConfig
from SetAnubis.examples.Selection.compact_sample import (
    build_selection_config,
    build_selection_pipeline,
    load_compact_dataframe,
)


def run_example():
    """Execute the real-event sample and return the full selection result."""
    pipeline = build_selection_pipeline()
    source = EventsBundleSource.from_events_dataframe(load_compact_dataframe())
    return pipeline.run(
        source,
        build_selection_config(),
        RunConfig(
            reweightLifetime=False,
            plotTrajectory=False,
            capture_intermediate=True,
        ),
    )


def main() -> None:
    """Print the cutflow and one-row-per-event stage summary."""
    result = run_example()
    print(f"Cut flow: {result['cutFlow']}")
    print(result["trace"].event_summary.to_string(index=False))


if __name__ == "__main__":
    main()
