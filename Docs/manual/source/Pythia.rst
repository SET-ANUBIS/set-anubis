.. _PythiaInterface:

Pythia Simulation Interface
===========================

The Pythia Simulation Interface provides a structured and modular way to configure and execute simulations for particle physics, particularly for Heavy Neutral Leptons (HNL) and Dark Photons. The interface relies on modular components and configuration files to handle particles, decays, and production processes.

It is composed of two main classes:

- `PythiaCMNDInterface`: To generate `.cmnd` config files for Pythia.
- `PythiaRunInterface`: To execute Pythia simulations based on those `.cmnd` files.

.. contents:: Contents
   :local:
   :depth: 2


CMND File Generation
--------------------

.. autoclass:: NeoSetAnubis.core.Pythia.adapters.input.pythia_cmnd_interface.PythiaCMNDInterface
   :members:
   :undoc-members:
   :show-inheritance:

This interface builds Pythia-compatible CMND cards based on model parameters, particle decays, and production channels. It connects directly to `NeoSetAnubisInterface` and `DecayInterface`, which provide access to internal particle definitions and decay data.


Example Usage:

.. code-block:: python

    from SetAnubis.core.Pythia.adapters.input.pythia_cmnd_interface import PythiaCMNDInterface

    interface = PythiaCMNDInterface(master_interface, decay_interface)
    interface.add_new_particles([9900012])
    interface.add_hard_production(hard_production_enum)
    card_str = interface.serialize()
    with open("hnl.cmnd", "w") as f:
        f.write(card_str)


Simulation Execution
--------------------

.. autoclass:: NeoSetAnubis.core.Pythia.adapters.input.pythia_run_interface.PythiaRunInterface
   :members:
   :undoc-members:
   :show-inheritance:

Once CMND cards are created, simulations can be executed with this interface. It takes care of directory management, output naming, and file generation.

Example:

.. code-block:: python

    from SetAnubis.core.Pythia.adapters.input.pythia_run_interface import PythiaRunInterface

    runner = PythiaRunInterface("outputs/")
    runner.ensure_directories(["lhe", "hepmc"])
    runner.process_file("hnl.cmnd", "outputs/lhe", "outputs/hepmc", 10000, suffix="scan1", include_time=True)


Command-Line Simulation Example
-------------------------------

You can use a CLI tool to configure and run simulations. Supported arguments:

.. code-block:: bash

    usage: Pythia Simulation
           [-h] [--model MODEL] [--particle PARTICLE] [--mass MASS]
           [--coupling COUPLING [COUPLING ...]] [--process PROCESS]
           [--may_decay MAY_DECAY] [--epsilon EPSILON]
           [--MesonMother MESONMOTHER]

    optional arguments:
      -h, --help
      --model MODEL
      --particle PARTICLE
      --mass MASS
      --coupling COUPLING ...
      --process PROCESS
      --may_decay MAY_DECAY
      --epsilon EPSILON
      --MesonMother MESONMOTHER


Scan Mode (Multi-CMND Interface)
--------------------------------

This module includes a flexible **multi-CMND generation** interface to scan over a grid of parameter values (mass, couplings, etc.) and generate `.cmnd` files with appropriate naming.

The key features of the scan system include:

- **Automatic naming** of `.cmnd` files based on the parameter values (e.g. `cmnd_mass1.0_coup1e-9.cmnd`)
- **Custom sweep logic**: select the parameters and ranges you want
- **Folder organization**: Output directories can be structured by parameter set
- **Integration with `PythiaRunInterface`** for batch simulations


Example:

.. code-block:: python

    # Assuming you have a scan manager (WIP interface)
    scan_manager = CMNDScanManager(base_dir="scan_outputs/")
    scan_manager.register_scan("mass", [0.5, 1.0, 2.0])
    scan_manager.register_scan("coupling", [1e-9, 5e-9])
    scan_manager.generate_all_cmnds()

    runner = PythiaRunInterface("scan_outputs/")
    runner.batch_run_from_folder("scan_outputs/configs", "scan_outputs/lhe", "scan_outputs/hepmc", num_events=10000)

This system is ideal for running multiple simulations for sensitivity studies or large-scale parameter exploration.

---

Particle Configuration Registration
-----------------------------------

Custom particle configurations can be added via the `register_config` decorator.

.. code-block:: python

    from Pythia_conf import register_config

    @register_config("MyNewParticle")
    class MyNewParticleConfig:
        # Your implementation here
        pass
