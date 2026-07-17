"""Tests for filesystem observation and custom logger helpers."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from uuid import uuid4

import pytest

import SetAnubis.core.Common.Observer as observer_module
from SetAnubis.core.Common.Logger import CustomLogger


class FakeWatchdogObserver:
    def __init__(self):
        self.scheduled = None
        self.started = False
        self.stopped = False
        self.joined = False

    def schedule(self, handler, directory, recursive=False):
        self.scheduled = (handler, directory, recursive)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def join(self):
        self.joined = True


def test_file_observer_lifecycle_and_callback(monkeypatch, tmp_path):
    monkeypatch.setattr(observer_module, "Observer", FakeWatchdogObserver)
    observer_module.FileObserver._instance = None

    file_observer = observer_module.FileObserver(str(tmp_path))
    calls = []
    target = str(tmp_path / "created.dat")
    file_observer.watch_file(target, calls.append)

    file_observer.start()
    assert file_observer.observer.started
    assert file_observer.observer.scheduled[1:] == (str(tmp_path), False)

    file_observer.event_handler.on_created(SimpleNamespace(src_path=target))
    file_observer.file_created(str(tmp_path / "ignored.dat"))
    assert calls == [target]

    file_observer.stop()
    assert file_observer.observer.stopped and file_observer.observer.joined
    assert observer_module.FileObserver(str(tmp_path)) is file_observer


def test_file_observer_requires_a_directory(monkeypatch):
    monkeypatch.setattr(observer_module, "Observer", FakeWatchdogObserver)
    observer_module.FileObserver._instance = None
    with pytest.raises(ValueError, match="Directory to watch"):
        observer_module.FileObserver().start()


def test_custom_logger_is_singleton_and_writes_to_file(tmp_path):
    name = f"setanubis-test-{uuid4()}"
    log_path = tmp_path / "logs" / "test.log"

    first = CustomLogger(name, str(log_path), level=logging.INFO)
    second = CustomLogger(name, str(tmp_path / "ignored.log"), level=logging.DEBUG)
    assert first is second

    logger = first.get_logger()
    logger.info("release audit message")
    for handler in logger.handlers:
        handler.flush()

    assert "release audit message" in log_path.read_text(encoding="utf-8")
