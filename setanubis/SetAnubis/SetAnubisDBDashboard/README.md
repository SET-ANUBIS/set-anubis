# SET-ANUBIS campaign database inspector

The campaign database inspector is the optional Dash application for auditing
generated samples, content-addressed artifacts and compact selection-ready event
bundles. Its purpose is to expose the provenance chain between a MadGraph/Pythia
campaign and the data products consumed by the SET-ANUBIS selection.

The application opens with a real demonstration workspace materialised from the
packaged CPC R5 resources: the seven-event HNL HepMC record, its compact
DataFrame bundle and its selection manifest. The default therefore works from an
installed wheel and does not point to a project-specific local directory.

## Scientific views

- **Campaign overview:** generated samples by UFO model, ingestion dates,
  cross-sections, scan coordinates and retained bundle frames.
- **Storage and provenance:** source HepMC records, generator folders, compact
  bundles, CAS artifacts and storage ratios.
- **Generated samples:** event identifiers, run names, LLP PDGs, seeds, bundle
  stage and retained artifacts.
- **Particle model:** masses, widths, charges, spins and decay channels parsed
  from stored SLHA banners.
- **Metadata records:** storage comparisons, bundle structure, scan parameters,
  widths and MadGraph provenance.

## Installation and launch

```bash
python -m pip install "SetAnubis[app]"
setanubis-db-dashboard --host 127.0.0.1 --port 8051
```

The packaged benchmark is selected by default. For a local campaign, choose
**Local SET-ANUBIS campaign** and provide:

```text
EventDatabase.db
EventsStorage/
MadGraph Events/   # optional; only required for provenance backfill
```

Equivalent command-line defaults can be supplied explicitly:

```bash
setanubis-db-dashboard \
  --db /path/to/EventsDatabase.db \
  --storage /path/to/EventsStorage \
  --events-root /path/to/MadGraph/Events \
  --host 127.0.0.1 \
  --port 8051
```

## Safety

The dashboard is an inspection layer. The storage backfill operation updates
metadata and should only be run against a controlled campaign database. The
geometry, selection thresholds and physics definitions remain in the
version-controlled core package.
