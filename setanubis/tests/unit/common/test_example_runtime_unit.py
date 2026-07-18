"""Tests for consistent console behaviour in executable examples."""

from __future__ import annotations

from SetAnubis.examples import _runtime


def test_example_entrypoint_displays_banner_once_and_preserves_exit_status(monkeypatch):
    calls: list[bool] = []
    monkeypatch.setattr(
        _runtime,
        "show_banner",
        lambda *, force: calls.append(force) or True,
    )

    assert _runtime.run_example_entrypoint(lambda: None) == 0
    assert _runtime.run_example_entrypoint(lambda: 7) == 7
    assert calls == [True, True]
