"""Inspect and evaluate decay functions extracted from a trusted UFO model."""

from __future__ import annotations

from SetAnubis import SetAnubisInterface, ufo_path
from SetAnubis.core.BranchingRatio.adapters.output.DecayProvider import DecayProvider


def main() -> int:
    """List available UFO decay channels and evaluate one when present."""
    model_path = str(ufo_path("UFO_HNL"))
    model = SetAnubisInterface(model_path)
    provider = DecayProvider(model_path)
    functions, parameter_names = provider.get_caches()

    # UFO modules are executable Python. Only inspect models from trusted sources.
    channel_count = sum(len(channels) for channels in functions.values())
    print(f"Cached UFO decay channels: {channel_count}")
    # Prefer the familiar Higgs-to-bottom channel when the UFO contains it.
    selected = None
    for mother, channels in functions.items():
        for daughters, function in channels.items():
            if mother == 25 and tuple(sorted(daughters)) == (-5, 5):
                selected = (mother, daughters, function)
                break
        if selected is not None:
            break
    if selected is None:
        raise RuntimeError("The UFO model contains no H -> b bbar decay channel")

    mother, daughters, function = selected
    required = parameter_names[mother][daughters]
    parameters = {name: model.get_parameter_value(name) for name in required}
    print("Example channel:", mother, list(daughters))
    print("Required parameters:", required)
    print("Calculated value:", function(parameters))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
