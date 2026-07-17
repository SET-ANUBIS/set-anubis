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
    """Return the bundled or checkout MARTY model mapping directory."""
    return asset_path("MARTY", "model")


@lru_cache(maxsize=2)
def _load_ufo_mappings(reversed: bool) -> Dict[str, str]:
    """Load merged MARTY-to-UFO parameter mappings from JSON and YAML."""
    assets_path = _model_assets_path()
    mapping: Dict[str, str] = {}

    json_file = assets_path / "conversion_sm.json"
    if json_file.is_file():
        data = json.loads(json_file.read_text(encoding="utf-8"))
        mapping.update(
            {
                entry["name"]: entry["ufo_name"]
                for entry in data
                if "name" in entry and "ufo_name" in entry
            }
        )

    yaml_file = assets_path / "conversion_model.yaml"
    if yaml_file.is_file():
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or []
        mapping.update(
            {
                entry["name"]: entry["ufo_name"]
                for entry in data
                if "name" in entry and "ufo_name" in entry
            }
        )

    return {value: key for key, value in mapping.items()} if reversed else mapping


def load_ufo_mappings(reversed: bool = False) -> Dict[str, str]:
    """Return cached MARTY/UFO parameter-name mappings."""
    return _load_ufo_mappings(reversed)


@lru_cache(maxsize=2)
def _load_particle_mappings(reversed: bool) -> Dict[str, str]:
    """Load merged PDG-to-MARTY particle mappings from JSON and YAML."""
    assets_path = _model_assets_path()
    mapping: Dict[str, str] = {}

    json_file = assets_path / "sm_particle.json"
    if json_file.is_file():
        data = json.loads(json_file.read_text(encoding="utf-8"))
        mapping.update(
            {
                str(entry["pdg_code"]): entry["name"]
                for entry in data
                if "pdg_code" in entry and "name" in entry
            }
        )

    yaml_file = assets_path / "model_particle.yaml"
    if yaml_file.is_file():
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or []
        mapping.update(
            {
                str(entry["pdg_code"]): entry["name"]
                for entry in data
                if "pdg_code" in entry and "name" in entry
            }
        )

    return {value: key for key, value in mapping.items()} if reversed else mapping


def load_particle_mappings(reversed: bool = False) -> Dict[str, str]:
    """Return cached PDG/MARTY particle-name mappings."""
    return _load_particle_mappings(reversed)
