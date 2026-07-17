Interactive Dash applications
=============================

SET-ANUBIS includes two optional Dash applications. They are intended for visual
inspection, validation and campaign auditing. They do not replace the
version-controlled geometry, selection or database APIs used to produce
scientific results.

Installation
------------

.. code-block:: bash

   python -m pip install "SetAnubis[app,selection]"

HepMC explorer
--------------

The HepMC explorer displays LLP production and decay vertices, charged and
neutral tracks, event-level kinematics and 2D/3D projections of the ATLAS cavern
and ANUBIS geometry. It is useful for checking coordinate conventions, decay
chains and representative events before a large selection campaign.

.. code-block:: bash

   setanubis-hepmc-explorer --host 127.0.0.1 --port 8050

The input HepMC path and event filters are selected in the application sidebar.
The displayed geometry is a diagnostic view; numerical acceptance should be
obtained from the selection pipeline.

Database dashboard
------------------

The database dashboard summarises imported model points, cross sections, cards,
banners, content-addressed artefacts, dataframe bundles and storage savings. It
can also inspect particle metadata extracted from stored banners.

.. code-block:: bash

   setanubis-db-dashboard \
      --db db/EventsDatabase.db \
      --storage db/EventsStorage \
      --events-root db/Events_THEO \
      --host 127.0.0.1 \
      --port 8051

The dashboard reads the existing catalogue and storage directories. Backfill
operations should be run only on a controlled copy or after the database has
been backed up.

Security and deployment
-----------------------

Both applications are development and analysis tools. They should be bound to
``127.0.0.1`` unless they are placed behind an authenticated reverse proxy.
Do not expose local event paths, databases or generator outputs directly to an
untrusted network.
