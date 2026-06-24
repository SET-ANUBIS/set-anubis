.. _PythiaInterface:

Pythia Simulation Interface
===========================

The Pythia interface provides two layers:

- ``PythiaCMNDInterface`` builds ``.cmnd`` cards: particles, decays, production channels and generic Pythia settings.
- ``PythiaRunInterface`` executes the C++/pybind11 Pythia runner and can apply runtime options, lifetimes, widths and event-level hard cuts.

The interface is particle-agnostic: every configurable method takes a PDG id and does not assume HNL ``9900012``.

CMND File Generation
--------------------

Example:

.. code-block:: python

    from SetAnubis.core.Pythia.adapters.input.PythiaCMNDInterface import PythiaCMNDInterface

    pid = 9900012  # replace with any BSM/modified particle PDG id
    interface = PythiaCMNDInterface(master_interface, decay_interface)

    interface.add_pythia_setting("PhaseSpace:pTHatMin", 20)
    interface.add_hard_production("HardQCD:hardbbbar")

    interface.set_particle_lifetime(pid, tau0_mm=1000.0)
    interface.set_particle_options(
        pid,
        mayDecay=True,
        isVisible=False,
        doForceWidth=True,
        extra_settings={"onMode": "on"},
    )
    interface.add_new_particles([pid])
    interface.add_decay_to_bsm_particles(pid)
    interface.add_decay_from_bsm_particles(pid)

    with open("model.cmnd", "w") as f:
        f.write(interface.serialize())

Runtime Generation Options
--------------------------

``PythiaRunInterface`` exposes runtime settings without requiring a new CMND card.
Hard cuts are applied after event generation and before writing LHE/HepMC outputs.

.. code-block:: python

    from SetAnubis.core.Pythia.adapters.input.PythiaRunInterface import PythiaRunInterface

    pid = 9900012
    runner = PythiaRunInterface(
        "outputs",
        new_particles=[pid],
        pythia_settings=["PhaseSpace:pTHatMin = 20"],
        lifetimes={pid: 1000.0},      # tau0 in mm
        widths={pid: 1e-12},          # mWidth in GeV
        hard_cuts=[{
            "pdg_id": pid,
            "min_pt": 30.0,
            "max_eta": 2.5,
            "min_count": 1,
            "use_abs_id": True,
            "final_only": False,
        }],
        max_trials=1_000_000,
    )

    runner.ensure_directories(["lhe", "hepmc", "text"])
    runner.process_file(
        "model.cmnd",
        "outputs/lhe",
        "outputs/hepmc",
        "outputs/text",
        num_events=10000,
        suffix="scan1",
    )

You can add cuts incrementally:

.. code-block:: python

    runner.add_hard_cut(pdg_id=13, min_pt=10.0, final_only=True, min_count=2)
    runner.set_lifetime(13, 1e20)
    runner.add_pythia_setting("ParticleDecays:tau0Max = 1e6")

Scan Mode
---------

``CMNDScanManager`` can now store the same particle options and generic settings before generating all cards:

.. code-block:: python

    scan_manager.register_scan("mass", [0.5, 1.0, 2.0])
    scan_manager.register_scan("coupling", [1e-9, 5e-9])
    scan_manager.set_new_particle(pid)
    scan_manager.set_particle_lifetime(pid, 1000.0)
    scan_manager.add_pythia_setting("PhaseSpace:pTHatMin", 20)
    scan_manager.generate_all_cmnds()
