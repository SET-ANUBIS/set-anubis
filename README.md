# SEnsitivity sTudies for ANUBIS: SET-ANUBIS
This repository contains a lightweight framework for the purpose of performing sensitivity studies of the ANUBIS experiment in the different potential geometry configurations (i.e. Shaft and ceiling) for a variety of LLP models.

The general framework will be composed of three main aspects:
- Event Generation:
  - item Different LLP models will be simulated in the ATLAS LHC environment.
  - There are benefits to different MC generators and so this will be set up such that the output of each of these is a common input to the next section. 
  - Currently planned for inclusion: MadGraph and Pythia8.
- Acceptance and selection:
  - This will take the output of the simulated events, and apply geometric acceptance cuts based on the work of Toby Satterthwaite to represent the possible detection of an LLP event within different geometric configurations of ANUBIS.
  - There will also be the ability to apply loose selection cuts here as appropriate e.g. number of layers of RPCs with hits, opening angles etc.
- Sensitivity determination:
  - Use the simulated events that pass the acceptance and selection criteria to determine ANUBIS' projected sensitivity to the specified LLP model. 
  - Create a set of plots with this sensitivity, which can include limits from other experiments where appropriate or possible, in a common style. 


Note: The framework is named for the Egyptian god, Set, in line with ANUBIS' namesake. Set is commonly considered the god of deserts, storms, and disorder. This is somewhat fitting for this framework as in sensitivity studies you are exploring a vast desert of parameter space that can feel quite disordered but we aim to map that desert and bring order to it. 


## Installation

### Python package only

```bash
python -m pip install .
setanubis-pythia-smoke
```

The default install is pure Python.  It lets you use the Python APIs and generate
Pythia CMND cards without requiring Pythia8/HepMC3 on the machine.

### Optional Pythia/HepMC3 runtime

To run Pythia from Python, compile the optional `pythia_sim` binding during
installation by passing the external dependency paths explicitly:

```bash
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
python -m pip install .[pythia]
```

For a local developer install of HepMC3 + Pythia8 first:

```bash
./External_Integration/install.sh HepMC3 Pythia
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
python -m pip install .[pythia]
```

Check the runtime with:

```bash
setanubis-pythia-check
```

When installing from a published PyPI wheel, pip will not compile native code.
To compile the optional binding from a published source distribution, use
`--no-binary SetAnubis` together with the same environment variables.

See `PYTHIA_PACKAGING.md` for details and PyPI/TestPyPI guidance.

## Generating the docs

If you want to have the docs in a local directory, you can follow this tutorial : 

```
cd Docs/manual
make html
xdg-open build/html/index.html
```

## Use the Branching Ratio calculator

Using the BRCalculator can be done in two ways. Either by using **python function** (you need to define function to calculate all the DecayWidths), or by using
the **file method**, where you put equation in a file (for example for channel (3,3), model HNl, particle N1, file db/HNL/N1/3_3.txt) and the equation will be evaluated.

If you're using the file method, you need to set the BR you want to use in "on" mode. This mean that in (for our last example) the db/HNL/Decays_brs/DecaySelection.conf you can put to on/off the BR channels you're interested in.

## Authors and acknowledgment
Sofie Erner
Anna Mullin
Théo Reymermier
Toby Satterthwaite 
Paul Swallow
