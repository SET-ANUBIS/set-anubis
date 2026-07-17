# SET-ANUBIS reproducibility package

This directory contains the lightweight, deterministic examples supplied with
SET-ANUBIS 1.0.0 for software verification and the planned *Computer Physics
Communications* submission.

The examples exercise five parts of the framework without downloading large
event samples or starting external generators:

| Directory | Reproduced operation | External program executed |
| --- | --- | --- |
| `core` | Parse the bundled HNL UFO and update a model parameter | No |
| `branching_ratio` | Interpolate two partial widths and branching ratios | No MARTY |
| `pythia` | Create and validate a generic Pythia CMND card | No Pythia runtime |
| `madgraph` | Create command, run, parameter, Pythia8 and MadSpin cards | No MadGraph/Docker |
| `selection` | Build selection dataframes from the compact real-event HNL CSV | No |

## Run

Use Python 3.10–3.12 from the repository root:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python reproducibility/run_all.py --output-dir reproducibility_outputs
```

A successful run creates `reproducibility_outputs/VALIDATED`. The generated
`results.json` is compared with `expected_results.json`; numerical comparisons
use a relative tolerance of `1e-12`. Card and selected-data files are checked by
SHA-256 hashes.

## Inputs and provenance

The model and example inputs are version-controlled with the source release:

- `setanubis/SetAnubis/assets/UFO/UFO_HNL/`;
- `setanubis/SetAnubis/examples/BranchingRatio/TestFiles/test_BR.csv`;
- `setanubis/SetAnubis/examples/Selection/InputFiles/hnl_selection_cutflow_df.csv.gz`.

UFO files are executable Python model definitions. Only run this package with
the files shipped by SET-ANUBIS or another source you trust. The selection reproducibility example reads the gzip CSV rather than the matching pickle bundle. The JSON manifest records source-event provenance.

## Scope

These examples validate software behavior and deterministic card/data
construction. Physics-production samples and publication plots require the
separately documented MadGraph, MARTY, Pythia8/HepMC3 and analysis environments.
Those large external runs are intentionally not part of this lightweight CPC
reproducibility package.
