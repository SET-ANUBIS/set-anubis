"""Generate JSON and HTML trace reports from seven real HNL events."""

from __future__ import annotations

import argparse
from pathlib import Path

from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource
from SetAnubis.core.Selection.domain.SelectionEngine import RunConfig
from SetAnubis.examples.Selection.compact_sample import (
    build_selection_config,
    build_selection_pipeline,
    load_compact_bundle,
)


def run_example(output_dir: str | Path) -> tuple[Path, Path]:
    """Run selection from the trusted packaged bundle and write both reports."""
    result = build_selection_pipeline().run(
        EventsBundleSource.from_bundle_dict(load_compact_bundle()),
        build_selection_config(),
        RunConfig(capture_intermediate=True),
    )
    trace = result["trace"]
    print(trace.event_summary.to_string(index=False))
    return trace.write_report(
        output_dir,
        basename="real_hnl_selection_trace",
        title="SET-ANUBIS compact real-event selection trace",
    )


def main() -> None:
    """Parse the output directory and generate the reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="selection_trace_output",
        help="Directory receiving the JSON and standalone HTML reports.",
    )
    args = parser.parse_args()
    json_path, html_path = run_example(args.output_dir)
    print(f"JSON report: {json_path}")
    print(f"HTML report: {html_path}")


if __name__ == "__main__":
    main()
