"""Unit tests for lightweight database providers and copy adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

import SetAnubis.core.DataBase.adapters.DecayProvider as decay_provider_module
import SetAnubis.core.DataBase.adapters.ParamsProvider as params_provider_module
import SetAnubis.core.DataBase.adapters.ParticleProvider as particle_provider_module
from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.DataBase.adapters.FileCopyBuilder import FileCopyBuilder
from SetAnubis.core.DataBase.adapters.ParamsProvider import ParamsProvider
from SetAnubis.core.DataBase.adapters.ParticleProvider import (
    ParticleProvider,
    ParticleType,
)


class FakeUFOManager:
    """Record provider calls without importing a real UFO model."""

    def __init__(self, path: str) -> None:
        self.path = path

    def get_sm_particles(self, evaluated: bool):
        return ("sm-particles", evaluated)

    def get_new_particles(self, evaluated: bool):
        return ("new-particles", evaluated)

    def get_all_particles(self, evaluated: bool):
        return ("all-particles", evaluated)

    def get_sm_params(self):
        return "sm-params"

    def get_param_with_sm_evaluation(self):
        return "evaluated-params"


class FakeDecayManager:
    """Minimal decay manager used to verify adapter initialization."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.events: list[str] = []
        daughters = MultiSet([11, -11])
        self.function = lambda values: values["width"]
        self.func = {23: {daughters: self.function}}

    def evaluate_with_sm(self) -> None:
        self.events.append("evaluate")

    def create_func_caches(self) -> None:
        self.events.append("cache")

    def get_caches(self):
        return {"ready": True}


def test_particle_and_parameter_providers_dispatch_to_ufo_manager(monkeypatch):
    monkeypatch.setattr(particle_provider_module, "UFOManager", FakeUFOManager)
    monkeypatch.setattr(params_provider_module, "UFOManager", FakeUFOManager)

    particles = ParticleProvider("model")
    assert particles.get(ParticleType.SM) == ("sm-particles", True)
    assert particles.get(ParticleType.NEW) == ("new-particles", True)
    assert particles.get(ParticleType.ALL) == ("all-particles", True)
    assert particles.get(object()) is None

    params = ParamsProvider("model")
    assert params.get(ParticleType.SM) == "sm-params"
    assert params.get(ParticleType.NEW) == "evaluated-params"
    assert params.get(ParticleType.ALL) == "evaluated-params"
    assert params.get(object()) is None


def test_decay_provider_initializes_and_exposes_functions(monkeypatch):
    monkeypatch.setattr(decay_provider_module, "DecayUFOManager", FakeDecayManager)
    provider = decay_provider_module.DecayProvider("model")

    assert provider.decay_manager.events == ["evaluate", "cache"]
    daughters = MultiSet([11, -11])
    assert provider.get_function(23, daughters)({"width": 0.25}) == 0.25
    assert provider.get_caches() == {"ready": True}


def test_file_copy_builder_copies_modifies_and_validates_sources(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("alpha beta", encoding="utf-8")
    copied = tmp_path / "nested" / "copied.txt"
    modified = tmp_path / "modified.txt"

    builder = FileCopyBuilder()
    assert builder.add_file(source, copied) is builder
    builder.add_file(source, modified, [("beta", "gamma")]).execute()

    assert copied.read_text(encoding="utf-8") == "alpha beta"
    assert modified.read_text(encoding="utf-8") == "alpha gamma"

    # Copying a file onto itself is a supported no-op.
    FileCopyBuilder().add_file(source, source).execute()
    assert source.read_text(encoding="utf-8") == "alpha beta"

    with pytest.raises(FileNotFoundError, match="source file does not exist"):
        FileCopyBuilder().add_file(tmp_path / "missing", copied).execute()
