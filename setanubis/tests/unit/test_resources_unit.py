"""Tests for repository and installed-package resource lookup."""

from __future__ import annotations

from pathlib import Path

import pytest

import SetAnubis.resources as resource_mod


def test_assets_environment_override_and_missing_asset(monkeypatch, tmp_path):
    assets = tmp_path / "Assets"
    model = assets / "UFO" / "Demo"
    model.mkdir(parents=True)
    monkeypatch.setenv("SETANUBIS_ASSETS_DIR", str(assets))

    assert resource_mod.assets_dir() == assets.resolve()
    assert resource_mod.ufo_path("Demo") == model.resolve()
    with pytest.raises(FileNotFoundError, match="asset not found"):
        resource_mod.asset_path("missing.dat")

    monkeypatch.setenv("SETANUBIS_ASSETS_DIR", str(tmp_path / "missing"))
    with pytest.raises(FileNotFoundError, match="non-existing"):
        resource_mod.assets_dir()


def test_packaged_assets_fallback_does_not_depend_on_cwd(monkeypatch, tmp_path):
    monkeypatch.delenv("SETANUBIS_ASSETS_DIR", raising=False)
    monkeypatch.setattr(resource_mod, "repository_root", lambda: None)
    monkeypatch.chdir(tmp_path)

    packaged = resource_mod.assets_dir()
    assert packaged.name == "assets"
    assert (packaged / "particles" / "particleData.json").is_file()


def test_repository_root_is_detected_for_editable_checkout():
    root = resource_mod.repository_root()
    assert root is not None
    assert (root / "pyproject.toml").is_file()
    assert (root / "Assets").is_dir()
