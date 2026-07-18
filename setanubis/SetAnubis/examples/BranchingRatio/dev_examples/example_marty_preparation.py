"""Prepare MARTY analytic source code without compiling or running MARTY."""

from __future__ import annotations

from SetAnubis.examples._runtime import run_example_entrypoint

import argparse
from pathlib import Path

from SetAnubis import SetAnubisInterface, ufo_path
from SetAnubis.core.BranchingRatio.domain.MartyTemplateManager import (
    MartyTemplateManager,
    TemplateType,
)


def prepare_marty_source(
    model: SetAnubisInterface,
    output_path: str | Path,
    *,
    model_name: str = "SM",
    mother: int = 23,
    daughters: tuple[int, ...] = (2, -2),
) -> Path:
    """Render one analytic MARTY source file without invoking a compiler."""
    template = MartyTemplateManager(
        model_name,
        [mother],
        list(daughters),
        TemplateType.ANALYTIC,
        model,
    )
    source = template.prepare()
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def main() -> int:
    """Write a prepared MARTY C++ source to a user-selected directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="marty_prepared/z_to_ddbar.cpp")
    args = parser.parse_args()
    model = SetAnubisInterface(str(ufo_path("UFO_HNL")))
    path = prepare_marty_source(model, args.output)
    print(f"Prepared MARTY source: {path}")
    print("No compiler or MARTY executable was launched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_example_entrypoint(main))
