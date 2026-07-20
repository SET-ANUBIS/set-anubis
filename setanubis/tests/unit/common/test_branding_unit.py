"""Tests for the process-level SET-ANUBIS console banner."""

from __future__ import annotations

from io import StringIO

from SetAnubis import branding


class _TTYBuffer(StringIO):
    def isatty(self) -> bool:
        return True


class _RedirectedBuffer(StringIO):
    def isatty(self) -> bool:
        return False


def setup_function() -> None:
    branding._reset_banner_state_for_tests()


def teardown_function() -> None:
    branding._reset_banner_state_for_tests()


def test_banner_is_emitted_once_in_interactive_mode(monkeypatch):
    monkeypatch.delenv("SETANUBIS_BANNER", raising=False)
    monkeypatch.setattr(
        branding,
        "_pythia_binding_status",
        lambda: "unavailable (CMND generation remains available)",
    )
    stream = _TTYBuffer()

    assert branding.show_banner(stream=stream) is True
    assert branding.show_banner(stream=stream) is False
    output = stream.getvalue()
    assert output.count(f" SET-ANUBIS {branding.__version__}") == 1
    assert "Théo Reymermier (lead) and Paul Swallow" in output
    assert "Contact: anubis-active@cern.ch" in output
    assert "Pythia binding: unavailable" in output
    assert "ANUBIS proceedings contribution" in output
    assert "arXiv:2512.14942" in output
    assert "Zenodo 10.5281/zenodo.21462101" in output


def test_banner_auto_mode_stays_quiet_for_redirected_output(monkeypatch):
    monkeypatch.delenv("SETANUBIS_BANNER", raising=False)
    stream = _RedirectedBuffer()

    assert branding.show_banner(stream=stream) is False
    assert stream.getvalue() == ""


def test_banner_environment_modes(monkeypatch):
    redirected = _RedirectedBuffer()
    monkeypatch.setenv("SETANUBIS_BANNER", "always")
    assert branding.show_banner(stream=redirected) is True

    branding._reset_banner_state_for_tests()
    monkeypatch.setenv("SETANUBIS_BANNER", "never")
    assert branding.show_banner(force=True, stream=_TTYBuffer()) is False


def test_banner_reports_available_pythia_binding_and_explicit_zenodo_doi(monkeypatch):
    monkeypatch.setenv("SETANUBIS_BANNER", "always")
    monkeypatch.setenv("SETANUBIS_ZENODO_DOI", "10.5281/zenodo.1234567")
    monkeypatch.setattr(
        branding,
        "_pythia_binding_status",
        lambda: "available (SetAnubis.core.Pythia.bindings.pythia_sim)",
    )
    stream = _RedirectedBuffer()

    assert branding.show_banner(stream=stream) is True
    output = stream.getvalue()
    assert "Pythia binding: available" in output
    assert "Zenodo 10.5281/zenodo.1234567" in output
