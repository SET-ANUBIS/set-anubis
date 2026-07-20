Console output and banners
==========================

SET-ANUBIS banner
-----------------

The public facade emits a compact SET-ANUBIS banner at most once per Python
process. The default ``auto`` mode displays it only when stdout is an interactive
terminal. This keeps CI logs and redirected batch output clean while retaining a
clear identity in ordinary command-line use.

The mode is controlled by ``SETANUBIS_BANNER``:

``auto``
   Display the banner only in an interactive terminal. This is the default.
``always``
   Display the banner even when stdout is redirected.
``never``
   Disable the banner.

The public helper can also request it explicitly:

.. code-block:: python

   from setanubis import show_banner

   show_banner(force=True)

The process-level guard prevents duplicate output when both ``setanubis`` and
``SetAnubis`` imports are used in the same analysis.  The banner also identifies
Théo Reymermier and Paul Swallow, reports whether the optional compiled Pythia
binding is available in the active environment, and reminds users to cite the
current ANUBIS proceedings contribution together with the corresponding Zenodo software release.

The ``1.0.0`` banner embeds the versioned Zenodo DOI
``10.5281/zenodo.21462101``. ``SETANUBIS_ZENODO_DOI`` can override this value
for development builds and later releases.

FastJet banner
--------------

FastJet prints a citation and licence banner the first time a clustering
sequence is created. SET-ANUBIS suppresses that console output by default so
that notebooks, batch jobs and CI logs remain concise.

Users can restore the upstream FastJet banner explicitly:

.. code-block:: bash

   export SETANUBIS_FASTJET_BANNER=1

or configure a clustering instance directly:

.. code-block:: python

   from setanubis import JetClustering, JetClusteringConfig

   clustering = JetClustering(
       JetClusteringConfig(show_banner=True)
   )

This option only controls console output. It does not alter the jet algorithm,
the resulting jets, or the requirement to cite FastJet in scientific work.
