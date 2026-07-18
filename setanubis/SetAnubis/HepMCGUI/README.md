# SET-ANUBIS HepMC selection explorer

The HepMC selection explorer is the optional Dash application for connecting a
generated event record to the ordered SET-ANUBIS selection. It combines the
ATLAS-cavern geometry, ANUBIS detector stations, LLP decay vertices, event
kinematics and an event-by-event selection trace in a single diagnostic view.

The application opens with the packaged seven-event HNL benchmark used by the
CPC reproducibility scenario **R5**. No local path is required for the first
launch. Each benchmark event is designed to stop at a different stage of the
selection, from the ANUBIS fiducial-volume requirement through the final
isolation cuts.

## Scientific views

- **Selection overview:** cumulative counts for `LLPDecay`, `InCavern`,
  `NotInATLAS`, detector geometry, tracking, MET, isolation and `Final`.
- **Decay geometry:** 2D and 3D views of the ATLAS cavern, exclusion envelope,
  ANUBIS ceiling/shaft stations and LLP vertices.
- **Kinematic diagnostics:** LLP momentum, pseudorapidity, missing transverse
  momentum, decay time and parent/daughter composition for the selected event
  subset.
- **Event inspection:** last passed stage, first failed stage, display-region class and
  the full HepMC decay topology for one event.

The display-region class is used only to organise geometric visualisation. Selection acceptance is determined by the canonical cumulative `InCavern` and `NotInATLAS` stages, so the plotting label cannot override or replace the cutflow decision.

The standard HNL profile uses the same configuration as R5: the packaged
`UFO_HNL` model, PDG identifier `9900012`, the ANUBIS ceiling geometry, a
30 GeV MET requirement, detector-intersection/tracking requirements and
`Delta R = 0.4` isolation thresholds. A generic LLP-inspection mode remains
available for custom samples when that benchmark selection is not appropriate.

## Installation and launch

```bash
python -m pip install "SetAnubis[app,selection]"
setanubis-hepmc-explorer --host 127.0.0.1 --port 8050
```

The packaged benchmark is selected by default. Choose **Local HepMC file** in
the sidebar to inspect another HepMC2 or HepMC3 record.

## Interpretation

The graphical interface is a diagnostic layer. Published cutflows and
acceptances must be produced by the version-controlled selection and geometry
APIs. The interface invokes that canonical pipeline for the standard HNL
profile; screenshots and interactive filters are not substitutes for archived
selection outputs.
