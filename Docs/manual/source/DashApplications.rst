Interactive analysis applications
=================================

SET-ANUBIS includes two optional Dash applications for event-level validation
and campaign auditing. They use the same packaged resources and core APIs as the
command-line workflows, but remain inspection layers: archived selection
outputs and version-controlled configuration are the source of truth for
scientific results.

Installation
------------

.. code-block:: bash

   python -m pip install "SetAnubis[app,selection]"

HepMC selection explorer
------------------------

The HepMC application connects generated LLP events to the ordered
SET-ANUBIS selection. It opens with the seven-event HNL benchmark used by the
CPC reproducibility scenario R5, so the first launch does not require a local
file path.

.. code-block:: bash

   setanubis-hepmc-explorer --host 127.0.0.1 --port 8050

The default HNL profile reproduces the canonical stages
``LLPDecay -> InCavern -> NotInATLAS -> Geometry -> Tracker -> MET ->
IsoJets -> IsoCharged -> IsoAll -> Final``. The interface reports cumulative
candidate counts, the first failed stage for every event, kinematic
distributions and 2D/3D detector geometry. A generic LLP mode can be selected
for custom HepMC files when the standard HNL configuration is not applicable.

The displayed ``InCavern`` stage is the configured ANUBIS fiducial decay region;
``NotInATLAS`` then applies the ATLAS detector-volume veto. This distinction is
important: the stages are ordered selection requirements, not independent
geometric labels.

The optional display-region class is a plotting aid only. It does not determine
acceptance and cannot replace the cumulative ``InCavern``/``NotInATLAS``
selection trace.

Campaign database inspector
----------------------------

The database application audits generator provenance, scan metadata,
content-addressed artifacts and compact selection-ready bundles. It also starts
with an internal demonstration workspace created from the packaged R5 HepMC
record, bundle and manifest.

.. code-block:: bash

   setanubis-db-dashboard --host 127.0.0.1 --port 8051

Choose **Local SET-ANUBIS campaign** in the sidebar to inspect an existing
catalogue. The corresponding command-line form is:

.. code-block:: bash

   setanubis-db-dashboard \
      --db /path/to/EventsDatabase.db \
      --storage /path/to/EventsStorage \
      --events-root /path/to/MadGraph/Events \
      --host 127.0.0.1 \
      --port 8051

The ``events-root`` argument is only required when refreshing storage
provenance from MadGraph run directories. Backfill operations update database
metadata and should therefore be performed on a controlled campaign database.

Security and deployment
-----------------------

Both applications are local analysis tools. Bind them to ``127.0.0.1`` unless
they are deployed behind an authenticated reverse proxy. Local event paths,
databases and generator outputs should not be exposed directly to an untrusted
network.
