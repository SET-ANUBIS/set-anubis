# ATLAS Cavern + HepMC BSM Explorer

An interactive Dash application for visualizing the ATLAS cavern geometry and overlaying the production and decay vertices of Beyond-the-Standard-Model (BSM) particles extracted from HepMC event files.

The application provides 2D and 3D event visualization tools, together with kinematic and topological filtering capabilities, to support the exploration of BSM event signatures in the ATLAS cavern environment.

## Features

- Visualization of the ATLAS cavern geometry in:
  - **XY projection**
  - **XZ projection**
  - **ZY projection**
  - **3D mode**
- Overlay of **production and decay vertices** for selected particles identified by **PDG ID**
- Display of **BSM particle tracks**
- Display of **daughter** and **granddaughter** particle tracks
- Color coding of particle tracks according to **charged** or **neutral** status
- Particle name display through the `particle` package
- **Event-by-event mode**, including:
  - an event table
  - dedicated 2D displays
  - dedicated 3D displays
- Kinematic filtering based on:
  - `E`
  - `pT`
  - `p`
  - `px`
  - `py`
  - `pz`
  - `eta`
  - `phi`
  - `theta`
- Topological filtering based on:
  - mother particles
  - daughter particles
- Simple **missing transverse energy (MET)** calculation
- Event filtering based on the **BSM decay region**:
  - outside ATLAS
  - inside ANUBIS

## Requirements

- Python 3.10+
- `dash`
- `plotly`
- `pandas`
- `numpy`
- `pyhepmc` (for HepMC2/3 ASCII files)

## Installation

Install the required dependencies with:

```bash
pip install -r requirements.txt
```

## Running the Application

Start the Dash application with:

```bash
python app.py
```

Then open the following address in your browser:

```text
http://127.0.0.1:8050
```

## Notes

- The cavern geometry is expressed in **meters**, consistently with `ATLASCavern`.
- HepMC vertex positions are often stored in **millimeters** (`length_unit` in HepMC). The application automatically converts them to meters.
- MadGraph/Pythia event samples are often defined relative to the **interaction point (IP)**. A dedicated toggle allows conversion from the IP frame to the cavern-center frame.

## Data Sources

The codebase is designed to support additional event sources through the `EventRepository` interface.

In particular, support for a **CSV/DataFrame-based backend** is planned. At present, CSV loading is **not yet implemented**; only a placeholder and the expected column specification are provided.

## Version 6 Highlights

- Event filtering according to the BSM decay region
- Full **event-by-event** exploration mode
- 2D and **3D** visualization for individual events
- Display of **BSM particle tracks** together with their daughter and granddaughter particles
- Improved particle rendering with charge-based color coding and particle names
