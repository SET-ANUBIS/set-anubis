"""Edit one run-card setting and print the resulting MadGraph card."""

from SetAnubis.core.MadGraph.adapters.input.RunCardBuilder import RunCardBuilder
from SetAnubis.examples._runtime import run_example_entrypoint


def main() -> int:
    """Override the event count while retaining the remaining defaults."""

    editor = RunCardBuilder()
    editor.set("nevents", 2000)
    print("Run card generated:\n")
    print(editor.serialize())
    return 0


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
