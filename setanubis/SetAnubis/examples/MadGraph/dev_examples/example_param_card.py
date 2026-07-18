"""Generate the default HNL parameter card from the packaged UFO model."""

from SetAnubis.core.MadGraph.adapters.input.ParamCardBuilder import ParamCardBuilder
from SetAnubis.examples._runtime import run_example_entrypoint
from SetAnubis.resources import ufo_path


def main() -> int:
    """Invoke the UFO-provided writer and print its default parameter card."""

    hnl_ufo_path = ufo_path("UFO_HNL")
    param_card = ParamCardBuilder(hnl_ufo_path / "write_param_card.py").serialize()
    print("Parameter card generated:\n")
    print(param_card)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
