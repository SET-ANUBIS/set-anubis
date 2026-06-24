# SetAnubisDBDashboard

Dash monitor for the SetAnubis `EventDatabaseManagerv3` database.

It uses the same dark Dash shell/style as the existing `HepMCGUI` app: sidebar controls, tabbed content, metric cards, Plotly graphs and Dash tables.

## Features

- Global database metrics: events, models, CAS blobs, stored bundles, HEPMC kept/removed.
- Storage monitoring: original `run_XX + run_XX_decayed_1` size vs stored `dict[str, DataFrame]` bundle size.
- Per-event storage plots and compression/savings ratios.
- Models table and event table with native Dash sorting/filtering.
- Bundle-frame summary from `bundle_metadata_json`.
- Particle catalog from stored MadGraph banners: MASS, DECAY, QNUMBERS, branching channels.
- Metadata explorer for storage, bundle, MadGraph cards/scan info.
- Storage backfill button calling `refresh_storage_metadata_from_events_root`.

## Install

From your repo root:

```bash
pip install -r SetAnubisDBDashboard/requirements.txt
```

Or add `dash`, `plotly` and `pandas` to your existing environment.

## Run

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

## Import resolution

The app tries to import `EventDatabaseManagerv3` from:

1. `setanubis.SetAnubis.core.DataBase.domain.EventDatabaseManagerv3`
2. `SetAnubis.core.DataBase.domain.EventDatabaseManagerv3`
3. `EventDatabaseManagerv3`

If needed, set:

```bash
export SETANUBIS_DB_MANAGER_PATH=/absolute/path/to/EventDatabaseManagerv3.py
```

## Font / branding

The stylesheet keeps the same CSS variables as `HepMCGUI`. When you send the font later, add it in your own project assets and set `--font` in `assets/styles.css`. Do not commit proprietary font files unless you have the right to distribute them.
