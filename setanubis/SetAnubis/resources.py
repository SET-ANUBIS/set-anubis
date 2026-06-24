"""Resource-location helpers for packaged and checkout-based SetAnubis assets.

The public API should not assume that the current working directory is the
repository root.  These helpers first honour an explicit environment override,
then look for a developer-checkout ``Assets`` directory, and finally fall back to
the lightweight assets shipped inside the Python package.
"""

from __future__ import annotations

import os
from importlib import resources as importlib_resources
from pathlib import Path

_ENV_ASSETS = "SETANUBIS_ASSETS_DIR"


def repository_root() -> Path | None:
    """Return the repository root when running from an editable checkout."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "Assets").is_dir() and (parent / "pyproject.toml").is_file():
            return parent
    return None


def assets_dir() -> Path:
    """Return the best available SetAnubis assets directory."""
    override = os.environ.get(_ENV_ASSETS)
    if override:
        path = Path(override).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(
                f"{_ENV_ASSETS} points to a non-existing path: {path}"
            )
        return path

    repo = repository_root()
    if repo is not None:
        return repo / "Assets"

    packaged = importlib_resources.files("SetAnubis") / "assets"
    return Path(str(packaged))


def asset_path(*parts: str) -> Path:
    """Return a concrete path inside the SetAnubis assets directory."""
    path = assets_dir().joinpath(*parts)
    if not path.exists():
        raise FileNotFoundError(
            f"SetAnubis asset not found: {path}. "
            f"Set {_ENV_ASSETS} to a custom Assets directory if needed."
        )
    return path


def ufo_path(name: str) -> Path:
    """Return the path to a bundled or checkout UFO model directory."""
    return asset_path("UFO", name)
