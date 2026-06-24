Pythia interface
================

SET-ANUBIS exposes two Pythia layers:

* ``PythiaCMNDInterface`` builds ``.cmnd`` cards for particles, decays,
  production channels and generic Pythia settings.
* ``PythiaRunInterface`` executes the optional C++/pybind11 runtime and supports
  particle-specific lifetimes, widths and hard cuts.

The interface is particle-agnostic. Methods accept a PDG id and do not assume a
specific HNL id.

CMND generation
---------------

.. code-block:: python

   from setanubis import PythiaCMNDInterface

   pid = 9900012
   interface = PythiaCMNDInterface(master_interface, decay_interface)
   interface.add_pythia_setting("PhaseSpace:pTHatMin", 20)
   interface.add_hard_production("HardQCD:hardbbbar")
   interface.set_particle_lifetime(pid, tau0_mm=1000.0)
   interface.set_particle_options(pid, mayDecay=True, isVisible=False)
   interface.add_new_particles([pid])

Runtime generation
------------------

.. code-block:: python

   from setanubis import PythiaRunInterface

   pid = 9900012
   runner = PythiaRunInterface(
       "outputs",
       new_particles=[pid],
       pythia_settings=["PhaseSpace:pTHatMin = 20"],
       lifetimes={pid: 1000.0},
       widths={pid: 1e-12},
       hard_cuts=[{
           "pdg_id": pid,
           "min_pt": 30.0,
           "max_eta": 2.5,
           "min_count": 1,
           "use_abs_id": True,
       }],
       max_trials=1_000_000,
   )

   print(runner.check_runtime())

The runtime requires the optional binding. See ``PYTHIA_PACKAGING.md`` for build
instructions.
