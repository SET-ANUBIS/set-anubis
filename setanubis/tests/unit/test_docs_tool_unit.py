"""Unit tests for the documentation build command."""

from __future__ import annotations

from pathlib import Path

import pytest

from SetAnubis.tools import docs


def test_repo_root_finds_checkout_from_nested_module(monkeypatch, tmp_path):
    root = tmp_path / "checkout"
    module = root / "setanubis" / "SetAnubis" / "tools" / "docs.py"
    module.parent.mkdir(parents=True)
    module.write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text("", encoding="utf-8")
    (root / "Docs" / "manual" / "source").mkdir(parents=True)
    monkeypatch.setattr(docs, "__file__", str(module))

    assert docs._repo_root() == root


def test_repo_root_reports_missing_sphinx_sources(monkeypatch, tmp_path):
    module = tmp_path / "installed" / "SetAnubis" / "tools" / "docs.py"
    module.parent.mkdir(parents=True)
    module.write_text("", encoding="utf-8")
    monkeypatch.setattr(docs, "__file__", str(module))

    with pytest.raises(RuntimeError, match="Cannot locate Docs/manual/source"):
        docs._repo_root()


def test_main_builds_strict_target_cleans_and_opens(monkeypatch, tmp_path, capsys):
    root = tmp_path / "checkout"
    source = root / "Docs" / "manual" / "source"
    build = root / "Docs" / "manual" / "build" / "dirhtml"
    source.mkdir(parents=True)
    build.mkdir(parents=True)
    (build / "obsolete.txt").write_text("old", encoding="utf-8")
    monkeypatch.setattr(docs, "_repo_root", lambda: root)

    calls: list[tuple[list[str], Path]] = []

    def fake_check_call(command, cwd):
        calls.append((command, cwd))
        assert not (build / "obsolete.txt").exists()
        build.mkdir(parents=True, exist_ok=True)
        (build / "index.html").write_text("<html></html>", encoding="utf-8")

    opened: list[str] = []
    monkeypatch.setattr(docs.subprocess, "check_call", fake_check_call)
    monkeypatch.setattr(docs.webbrowser, "open", opened.append)

    assert docs.main(["--clean", "--strict", "--open", "--builder", "dirhtml"]) == 0
    command, cwd = calls[0]
    assert command[:5] == [docs.sys.executable, "-m", "sphinx", "-b", "dirhtml"]
    assert "-W" in command
    assert command[-2:] == [str(source), str(build)]
    assert cwd == root
    assert opened == [(build / "index.html").as_uri()]
    assert "Documentation built at" in capsys.readouterr().out


def test_main_does_not_open_missing_index(monkeypatch, tmp_path):
    root = tmp_path / "checkout"
    (root / "Docs" / "manual" / "source").mkdir(parents=True)
    monkeypatch.setattr(docs, "_repo_root", lambda: root)
    monkeypatch.setattr(docs.subprocess, "check_call", lambda *_args, **_kwargs: None)
    opened: list[str] = []
    monkeypatch.setattr(docs.webbrowser, "open", opened.append)

    assert docs.main(["--open"]) == 0
    assert opened == []
