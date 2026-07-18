# SET-ANUBIS CPC reproducibility suite

This directory contains five deterministic, release-scale reproductions. They
exercise the scientific software path without launching a publication-scale
Monte Carlo campaign or requiring MARTY, MadGraph, Docker or the native Pythia
runtime.

## Directory contract

Each scenario follows the same structure:

```text
R<N>_<name>/
├── README.md
├── input/             # version-controlled configuration or small input data
├── expected_output/   # version-controlled reference summary
├── output/            # generated locally; ignored by Git
└── run.py              # independently executable scenario
```

The large or canonical scientific inputs already distributed by the Python
package are referenced from `input/config.json` rather than duplicated. In
particular, R5 reads the compact seven-event HepMC2 sample packaged under
`SetAnubis.examples.Selection.InputFiles`.

## Scenarios

| ID | Component | Deterministic result | External runtime |
| --- | --- | --- | --- |
| R1 | Core/model interface | UFO content and parameter update | none |
| R2 | Branching ratio | partial widths, total width and BRs | none |
| R3 | Pythia | `.cmnd` generation and SHA-256 | Pythia not run |
| R4 | MadGraph | command/run/param/shower/MadSpin cards | MadGraph/Docker not run |
| R5 | Selection | HepMC conversion, cutflow and JSON/HTML trace | no generator run |

## Run all scenarios

Install the release with the selection extra because R5 reads HepMC:

```bash
python -m pip install -e ".[dev,selection]"
python reproducibility/run_reproducibility.py
```

The default command writes generated files into each scenario's `output/`
directory and compares `summary.json` with `expected_output/summary.json`.
Successful scenarios receive a `VALIDATED` marker.

For CI or an archival run, place all outputs below one directory:

```bash
python reproducibility/run_reproducibility.py \
  --output-root reproducibility_outputs
```

Run one scenario independently:

```bash
python reproducibility/R5_selection/run.py
python reproducibility/run_reproducibility.py --scenario R5
```

## Interpretation

These scenarios establish that a tagged release reproduces selected deterministic
software results. They do **not** reproduce the complete event-generation
campaign used for a physics publication. Publication-scale reproduction also
requires the archived generator versions, container digests, random seeds,
campaign cards, scan definitions and larger benchmark datasets described by the
associated analysis record.

The generated `output/` directories are intentionally excluded from Git. For a
CPC submission or release audit, archive the combined output directory together
with the exact SET-ANUBIS tag, environment description and distribution
checksums.
