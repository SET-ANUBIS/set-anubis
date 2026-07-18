"""Packaged demonstration inputs for the HepMC explorer."""

from __future__ import annotations

import os
import shutil
import tempfile
from importlib.resources import as_file, files
from pathlib import Path

_DEMO_FILENAME = "hnl_selection_cutflow.hepmc.gz"


def demo_hepmc_path() -> Path:
    """Return a stable real path to the packaged seven-event HNL benchmark.

    ``importlib.resources`` may expose package data through a temporary or
    virtual filesystem.  The Dash application needs a path that remains valid
    for the lifetime of the server, so the resource is copied once into a
    process-independent cache below the operating-system temporary directory.
    """
    override = os.environ.get("SETANUBIS_HEPMC_PATH")
    if override:
        return Path(override).expanduser().resolve()

    resource = files("SetAnubis.examples.Selection").joinpath(
        "InputFiles", _DEMO_FILENAME
    )
    cache_root = Path(
        os.environ.get(
            "SETANUBIS_DEMO_CACHE",
            Path(tempfile.gettempdir()) / "setanubis-dashboard-demo-v1",
        )
    )
    cache_root.mkdir(parents=True, exist_ok=True)
    target = cache_root / _DEMO_FILENAME

    with as_file(resource) as source:
        source_path = Path(source)
        if not target.exists() or target.stat().st_size != source_path.stat().st_size:
            shutil.copy2(source_path, target)
    return target


def is_demo_hepmc(path: str | os.PathLike[str] | None) -> bool:
    """Return whether *path* points to the materialised benchmark input."""
    if not path:
        return False
    try:
        return Path(path).resolve() == demo_hepmc_path().resolve()
    except OSError:
        return False
