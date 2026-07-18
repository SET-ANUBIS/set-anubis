"""Create and print a minimal MadSpin decay card without running MadGraph."""

from SetAnubis.core.MadGraph.domain.MadspinCardBuilder import MadSpinCardBuilder
from SetAnubis.examples._runtime import run_example_entrypoint


def main() -> int:
    """Build one illustrative decay entry and serialize the card."""

    builder = MadSpinCardBuilder()
    builder.add_decay("decay n1 > ell ell vv")
    print("MadSpin card generated:\n")
    print(builder.serialize())
    return 0


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
