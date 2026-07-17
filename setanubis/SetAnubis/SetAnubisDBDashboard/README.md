# SET-ANUBIS DB dashboard

The database dashboard is an optional Dash application for auditing generated
campaigns and selection-ready event bundles.  It is designed to answer practical
questions during a scan: which parameter points were generated, which cards and
banners were stored, how much disk space was saved by dataframe bundles, and
which samples are ready for selection.

## Physics role

SET-ANUBIS stores generator provenance separately from the final acceptance
calculation.  For a MadGraph scan this can include job scripts, run cards,
parameter cards, MadSpin cards, shower cards, banners, scan metadata, HepMC
references and compact `dict[str, DataFrame]` bundles.  The dashboard exposes
that information without modifying the database schema or the selection logic.

## Features

- Global metrics for events, models, CAS blobs, bundles and retained/removed
  HepMC records.
- Per-run storage monitoring for original MadGraph event folders versus compact
  dataframe bundles.
- Model and event tables with Dash sorting/filtering.
- Particle and decay-channel summaries extracted from stored banners.
- Metadata browser for cards, scan points and bundle metadata.
- Backfill helper for refreshing storage metadata from an existing events root.

## Installation

From the repository root:

```bash
python -m pip install -e ".[app]"
```

or from PyPI:

```bash
python -m pip install "SetAnubis[app]"
```

## Running

```bash
python SetAnubisDBDashboard/run_db_dashboard.py \
  --db db/EventsDatabase.db \
  --storage db/EventsStorage \
  --events-root db/Events_THEO \
  --host 127.0.0.1 \
  --port 8050 \
  --debug
```

Then open the local Dash URL printed by Dash.

## Notes

The dashboard is an inspection layer only.  Selection definitions, geometry cuts,
MET thresholds and isolation requirements are defined in the core selection code
and should be version controlled alongside campaign outputs.
