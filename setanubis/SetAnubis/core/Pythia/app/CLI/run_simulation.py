def run_simulation(config_path, param_overrides):
    import yaml
    from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
    from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface, CalculationDecayStrategy
    from SetAnubis.core.Pythia.adapters.input.pythia_cmnd_interface import PythiaCMNDInterface
    from SetAnubis.core.Pythia.app.CLI.utils.prod_logic import PROD_TO_HARDQCD
    import os
    from pathlib import Path

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    nsa = SetAnubisInterface(config["model_path"])
    nsa.set_leaf_param("mN1", config["mass"])

    particle = config["particle"]
    
    for override in param_overrides:
        if '=' in override:
            name, val = override.split('=')
            try:
                nsa.set_leaf_param(name.strip(), float(val))
            except ValueError:
                print(f"⚠️ Cannot convert '{val}' to float for param '{name}'")

    decay_interface = DecayInterface(nsa)

    if config.get("decay", {}).get("enabled", False):
        decay_type = config["decay"].get("type", "all")
        decay_list = [
            {"mother": particle, "daughters": [12, -12, 12]},
            {"mother": particle, "daughters": [-11, 11, 12]}
            # etc.
        ] if decay_type == "all" else []
        decay_interface.add_decays(
            decay_list,
            CalculationDecayStrategy.PYTHON,
            {"script_path": os.path.join(os.path.dirname(__file__), "TestFiles", "HNL_eq.py")}
        )

    prod_decays = [
        {"mother": 4132, "daughters": [particle, -11, 3312]},
        {"mother": 421, "daughters": [particle, -13, -321]}
    ]
    decay_interface.add_decays(
        prod_decays,
        CalculationDecayStrategy.PYTHON,
        {"script_path": os.path.join(os.path.dirname(__file__), "TestFiles", "production_eq.py")}
    )

    command = PythiaCMNDInterface(nsa, decay_interface)
    command.change_sm_particles([4132], Path(config["change_sm_particles"]))
    command.add_new_particles([particle])

    for prod in config.get("production", []):
        for hard in PROD_TO_HARDQCD.get(prod, []):
            command.add_hard_production(hard)

    command.add_decay_to_bsm_particles(particle)
    command.add_decay_from_bsm_particles(particle)

    print("✅ CMND generated:\n")
    print(command.serialize())
