"""Create and print the default Pythia shower card used by MadGraph."""

from SetAnubis.core.MadGraph.adapters.input.PythiaCardBuilder import PythiaCardBuilder
from SetAnubis.examples._runtime import run_example_entrypoint


def main() -> int:
    """Serialize the default shower settings without creating files."""

    print("Pythia card generated:\n")
    print(PythiaCardBuilder().serialize())
    return 0


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
