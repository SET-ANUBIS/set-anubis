"""Contract tests for opt-in FastJet banner display."""

from __future__ import annotations

from SetAnubis.core.Selection.domain.JetBuilder import JetClusteringConfig


def test_fastjet_banner_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SETANUBIS_FASTJET_BANNER", raising=False)
    assert JetClusteringConfig().show_banner is False


def test_fastjet_banner_can_be_enabled_explicitly(monkeypatch):
    assert JetClusteringConfig(show_banner=True).show_banner is True
    monkeypatch.setenv("SETANUBIS_FASTJET_BANNER", "1")
    assert JetClusteringConfig().show_banner is True


def test_fastjet_stream_is_temporarily_disabled_when_supported(monkeypatch):
    from SetAnubis.core.Selection.domain import JetBuilder as jet_builder

    calls = []
    original_stream = object()

    class _ClusterSequence:
        current = original_stream

        @classmethod
        def fastjet_banner_stream(cls):
            return cls.current

        @classmethod
        def set_fastjet_banner_stream(cls, value):
            calls.append(value)
            cls.current = value

    monkeypatch.setattr(jet_builder.fastjet, "ClusterSequence", _ClusterSequence)

    with jet_builder._suppress_fastjet_banner(enabled=True):
        assert _ClusterSequence.current is None

    assert calls == [None, original_stream]
    assert _ClusterSequence.current is original_stream
