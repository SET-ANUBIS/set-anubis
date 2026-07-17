# SET-ANUBIS HepMC explorer

The HepMC explorer is the optional Dash application for inspecting generated signal
events in the ATLAS cavern and ANUBIS detector geometry.  It is intended for
validation and debugging, not for defining the production selection.  The physics
selection used in scans lives in the `SelectionEngine` and geometry adapters.

## Use case

After a MadGraph/Pythia campaign has produced HepMC events, the GUI can overlay
production vertices, LLP decay vertices and charged/neutral decay products on the
same cavern geometry used by the selection code.  This is useful for checking HNL
or scalar LLP samples before running large cutflow campaigns.

## Features

- ATLAS cavern and ANUBIS geometry in XY, XZ, ZY and 3D projections.
- Event-by-event navigation through HepMC samples.
- PDG-ID based LLP selection.
- Production and decay vertex overlays.
- Daughter and granddaughter track display.
- Charged/neutral track rendering.
- Kinematic filters for `E`, `pT`, `p`, `px`, `py`, `pz`, `eta`, `phi` and `theta`.
- Simple MET inspection.
- Region checks for decays inside ATLAS, inside the cavern and near ANUBIS.

## Installation

From the repository root:

```bash
python -m pip install -e ".[app,selection]"
```

For a package install:

```bash
python -m pip install "SetAnubis[app,selection]"
```

## Running

From this directory:

```bash
python app.py
```

Then open the local Dash URL printed in the terminal, usually:

```text
http://127.0.0.1:8050
```

## Coordinate convention

Generated events are usually expressed relative to the interaction point, while
the cavern geometry uses the `ATLASCavern` coordinate convention.  The app
contains conversion controls to make this visible during debugging.  Always use
the production selection code, not a GUI screenshot, as the source of truth for
published acceptances.
