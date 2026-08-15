"""Mapping and deterministic naming helpers for MARTY workspaces."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml

from SetAnubis.resources import asset_path


def decay_name(
    mother: int | Iterable[int],
    daughters: Iterable[int],
    nsa: Any,
    mapping: dict,
) -> str:
    """Build a stable process name from mother and daughter PDG identifiers.

    ``nsa`` and ``mapping`` remain in the signature for compatibility with the
    existing MARTY orchestration API. Names currently use absolute PDG codes so
    that generated paths stay independent of model display names.
    """
    del nsa, mapping
    mothers = list(mother) if isinstance(mother, (list, tuple, set)) else [mother]
    mother_names = [str(abs(int(value))) for value in mothers]
    daughter_names = [str(abs(int(value))) for value in daughters]
    return "_".join(mother_names + ["s"] + daughter_names)


def _model_assets_path() -> Path:
    """Return the bundled or checkout MARTY model/mapping directory.

    The historical private helper name is kept because release-contract tests
    and downstream debugging utilities use it to redirect mappings.
    """
    return asset_path("MARTY", "model")


def _default_mapping_dir() -> Path:
    return _model_assets_path()


def _normalise_mapping_dir(mapping_dir: str | Path | None) -> str:
    path = _default_mapping_dir() if mapping_dir is None else Path(mapping_dir)
    path = path.expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"MARTY mapping directory not found: {path}")
    return str(path)


def _load_mapping_file(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    elif path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    else:
        raise ValueError(f"Unsupported MARTY mapping format: {path}")
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of mapping entries in {path}")
    return data


@lru_cache(maxsize=32)
def _load_ufo_mappings_cached(reversed: bool, mapping_dir: str) -> Dict[str, str]:
    """Load merged MARTY-to-UFO parameter mappings from one directory."""
    assets_path = Path(mapping_dir)
    mapping: Dict[str, str] = {}

    for file_name in ("conversion_sm.json", "conversion_model.yaml"):
        for entry in _load_mapping_file(assets_path / file_name):
            if "name" in entry and "ufo_name" in entry:
                mapping[str(entry["name"])] = str(entry["ufo_name"])

    return {value: key for key, value in mapping.items()} if reversed else mapping


@lru_cache(maxsize=2)
def _load_ufo_mappings(reversed: bool) -> Dict[str, str]:
    """Backward-compatible cached loader for the default mapping directory."""
    return _load_ufo_mappings_cached(reversed, str(_model_assets_path().resolve()))


def load_ufo_mappings(
    reversed: bool = False,
    mapping_dir: str | Path | None = None,
) -> Dict[str, str]:
    """Return cached MARTY/UFO parameter-name mappings.

    Args:
        reversed: Return UFO-to-MARTY rather than MARTY-to-UFO names.
        mapping_dir: Optional directory containing ``conversion_sm.json`` and
            ``conversion_model.yaml``.  When omitted, the packaged/check-out
            SET-ANUBIS mapping directory is used.
    """
    if mapping_dir is None:
        return _load_ufo_mappings(reversed)
    return _load_ufo_mappings_cached(reversed, _normalise_mapping_dir(mapping_dir))


@lru_cache(maxsize=32)
def _load_particle_mappings_cached(reversed: bool, mapping_dir: str) -> Dict[str, str]:
    """Load merged PDG-to-MARTY particle mappings from one directory."""
    assets_path = Path(mapping_dir)
    mapping: Dict[str, str] = {}

    for file_name in ("sm_particle.json", "model_particle.yaml"):
        for entry in _load_mapping_file(assets_path / file_name):
            if "pdg_code" in entry and "name" in entry:
                mapping[str(entry["pdg_code"])] = str(entry["name"])

    return {value: key for key, value in mapping.items()} if reversed else mapping


@lru_cache(maxsize=2)
def _load_particle_mappings(reversed: bool) -> Dict[str, str]:
    """Backward-compatible cached loader for the default mapping directory."""
    return _load_particle_mappings_cached(reversed, str(_model_assets_path().resolve()))


def load_particle_mappings(
    reversed: bool = False,
    mapping_dir: str | Path | None = None,
) -> Dict[str, str]:
    """Return cached PDG/MARTY particle-name mappings.

    Args:
        reversed: Return MARTY-to-PDG rather than PDG-to-MARTY names.
        mapping_dir: Optional directory containing ``sm_particle.json`` and
            ``model_particle.yaml``.  This makes a checkout mapping usable even
            when the Python package itself is imported from ``site-packages``.
    """
    if mapping_dir is None:
        return _load_particle_mappings(reversed)
    return _load_particle_mappings_cached(
        reversed,
        _normalise_mapping_dir(mapping_dir),
    )


def clear_mapping_caches() -> None:
    """Clear mapping caches after editing mapping files in a live process."""
    _load_ufo_mappings.cache_clear()
    _load_particle_mappings.cache_clear()
    _load_ufo_mappings_cached.cache_clear()
    _load_particle_mappings_cached.cache_clear()
