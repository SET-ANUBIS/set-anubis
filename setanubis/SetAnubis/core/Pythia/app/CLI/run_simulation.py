def _normalise_decay_channels(channels, default_particle=None):
    if not channels:
        return []
    result = []
    for item in channels:
        mother = item.get("mother", default_particle)
        daughters = item.get("daughters", [])
        if mother is None or not daughters:
            continue
        result.append({"mother": int(mother), "daughters": [int(x) for x in daughters]})
    return result


def _apply_params(nsa, params):
    for name, value in (params or {}).items():
        try:
            nsa.set_leaf_param(str(name), float(value))
        except ValueError:
            print(f"⚠️ Cannot convert '{value}' to float for param '{name}'")


def run_simulation(config_path, param_overrides):
    import os
    from pathlib import Path
    import yaml
    from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
    from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface, CalculationDecayStrategy
    from SetAnubis.core.Pythia.adapters.input.PythiaCMNDInterface import PythiaCMNDInterface
    from SetAnubis.core.Pythia.app.CLI.utils.prod_logic import PROD_TO_HARDQCD

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    nsa = SetAnubisInterface(config["model_path"])
    particle = int(config["particle"])

    # Generic parameter support. For the legacy HNL config, mass_parameter defaults to mN1.
    mass_parameter = config.get("mass_parameter", "mN1" if "mass" in config else None)
    if mass_parameter and "mass" in config:
        nsa.set_leaf_param(mass_parameter, float(config["mass"]))

    _apply_params(nsa, config.get("custom_params", {}))

    for override in param_overrides:
        if "=" in override:
            name, val = override.split("=", 1)
            try:
                nsa.set_leaf_param(name.strip(), float(val))
            except ValueError:
                print(f"⚠️ Cannot convert '{val}' to float for param '{name}'")

    decay_interface = DecayInterface(nsa)

    decay_config = config.get("decay", {})
    if decay_config.get("enabled", False):
        decay_channels = _normalise_decay_channels(decay_config.get("channels"), default_particle=particle)

        # Backwards-compatible HNL example if no explicit channels are provided.
        if not decay_channels and decay_config.get("type", "all") == "all":
            decay_channels = [
                {"mother": particle, "daughters": [12, -12, 12]},
                {"mother": particle, "daughters": [-11, 11, 12]},
            ]

        script_path = decay_config.get(
            "script_path",
            os.path.join(os.path.dirname(__file__), "TestFiles", "HNL_eq.py"),
        )
        if decay_channels:
            decay_interface.add_decays(
                decay_channels,
                CalculationDecayStrategy.PYTHON,
                {"script_path": script_path},
            )

    production_decays = _normalise_decay_channels(config.get("production_decays"))
    if not production_decays and config.get("legacy_hnl_production", True):
        production_decays = [
            {"mother": 4132, "daughters": [particle, -11, 3312]},
            {"mother": 421, "daughters": [particle, -13, -321]},
        ]

    if production_decays:
        production_script = config.get(
            "production_script_path",
            os.path.join(os.path.dirname(__file__), "TestFiles", "production_eq.py"),
        )
        decay_interface.add_decays(
            production_decays,
            CalculationDecayStrategy.PYTHON,
            {"script_path": production_script},
        )

    command = PythiaCMNDInterface(nsa, decay_interface)

    for setting in config.get("pythia_settings", []):
        if isinstance(setting, dict):
            command.add_pythia_setting(setting["key"], setting.get("value"))
        else:
            command.add_pythia_setting(setting)

    particle_options = config.get("particle_options", {})
    if particle_options:
        # YAML keys may be strings.
        for pdg, options in particle_options.items():
            command.set_particle_options(int(pdg), **options)

    change_sm_particles = config.get("change_sm_particles")
    if change_sm_particles:
        if isinstance(change_sm_particles, str):
            command.change_sm_particles([4132], Path(change_sm_particles))
        else:
            for item in change_sm_particles:
                command.change_sm_particles([int(x) for x in item["particles"]], Path(item["file"]))

    command.add_new_particles([particle])

    for prod in config.get("production", []):
        if prod in PROD_TO_HARDQCD:
            for hard in PROD_TO_HARDQCD[prod]:
                command.add_hard_production(hard)
        else:
            command.add_hard_production(prod)

    command.add_decay_to_bsm_particles(particle)
    command.add_decay_from_bsm_particles(particle)

    cmnd_text = command.serialize()
    output_cmnd = config.get("output_cmnd")
    if output_cmnd:
        Path(output_cmnd).write_text(cmnd_text)
        print(f"✅ CMND written to {output_cmnd}")
    else:
        print("✅ CMND generated:\n")
        print(cmnd_text)
