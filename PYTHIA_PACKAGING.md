# Optional Pythia/HepMC3 packaging policy

Pythia is a supporting backend in SET-ANUBIS.  The release documentation keeps
MadGraph generation and geometry/selection as the main public workflow, while the
Pythia layer remains available for standalone generation and cross-checks.

## Why the binding is optional

Pythia8 and HepMC3 are external C++ projects.  Building them automatically during
an ordinary `pip install SetAnubis` would make installation slow, platform
sensitive and difficult to debug.  Therefore:

- the default wheel is Python-only;
- `.cmnd` generation works without native Pythia;
- runtime generation is compiled only when `SETANUBIS_BUILD_PYTHIA=1` is set.

## Build with external installations

```bash
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \
SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \
python -m pip install --no-binary SetAnubis "SetAnubis[pythia]"
```

`SETANUBIS_PYTHIA8_DIR` should point to a Pythia installation prefix containing
`include/Pythia8/Pythia.h` and `lib/libpythia8.*`.  `SETANUBIS_HEPMC3_DIR` should
point to a HepMC3 installation prefix containing `include/HepMC3/GenEvent.h` and
`lib/libHepMC3.*`.

## Build local external copies

```bash
./External_Integration/install.sh HepMC3 Pythia
SETANUBIS_BUILD_PYTHIA=1 \
SETANUBIS_PYTHIA8_DIR=$PWD/External_Integration/Pythia/pythia8315 \
SETANUBIS_HEPMC3_DIR=$PWD/External_Integration/HepMC3/hepmc3-install \
python -m pip install -e ".[pythia]"
```

## Diagnostics

```bash
setanubis-pythia-check
```

This command reports whether the binding can be imported and which Pythia/HepMC3
paths are visible.

## Runtime notes

If the extension imports during build but fails at runtime, check the dynamic
library path:

```bash
export LD_LIBRARY_PATH=/path/to/pythia8/lib:/path/to/hepmc3/lib:$LD_LIBRARY_PATH
```

On macOS use `DYLD_LIBRARY_PATH` instead, subject to the usual macOS SIP
limitations.
