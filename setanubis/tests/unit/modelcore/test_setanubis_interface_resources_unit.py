"""Tests for resource resolution in the public model interface."""

from __future__ import annotations

from SetAnubis import SetAnubisInterface, ufo_path


def test_interface_resolves_particle_metadata_outside_repository_cwd(
    monkeypatch, tmp_path
):
    """The public interface must not depend on the repository working directory."""
    monkeypatch.chdir(tmp_path)

    interface = SetAnubisInterface(str(ufo_path("UFO_HNL")))

    particle = interface.get_particle_info(24)
    assert particle["pdg_code"] == 24
    assert interface.get_particle_mass(24) is not None
