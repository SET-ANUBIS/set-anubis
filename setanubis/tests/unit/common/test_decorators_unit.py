"""Unit tests for reusable function decorators."""

from __future__ import annotations

import logging

import pytest

import SetAnubis.core.Common.Decorators as decorators


def test_timing_logging_and_tracing_decorators(monkeypatch, capsys, caplog):
    times = iter([1.0, 1.125])
    monkeypatch.setattr(decorators.time, "time", lambda: next(times))

    @decorators.timing_decorator
    def add(left, right=0):
        return left + right

    assert add(2, right=3) == 5
    assert "took 0.1250 seconds" in capsys.readouterr().out

    @decorators.log_decorator
    def multiply(left, right):
        return left * right

    with caplog.at_level(logging.DEBUG):
        assert multiply(2, 4) == 8
    assert "Calling function multiply" in caplog.text
    assert "returned 8" in caplog.text

    @decorators.tracing_decorator
    def identity(value):
        return value

    assert identity("value") == "value"
    trace = capsys.readouterr().out
    assert "Entering identity" in trace and "Exiting identity" in trace


def test_validation_memoization_and_return_type_checks():
    @decorators.validate_inputs((int, str))
    def combine(number, text):
        return f"{number}:{text}"

    assert combine(2, "x") == "2:x"
    with pytest.raises(TypeError, match="Expected type"):
        combine("2", "x")

    calls = []

    @decorators.memoize
    def square(value):
        calls.append(value)
        return value * value

    assert square(3) == square(3) == 9
    assert calls == [3]

    @decorators.return_type_checker(int)
    def valid_result():
        return 1

    @decorators.return_type_checker(int)
    def invalid_result():
        return "1"

    assert valid_result() == 1
    with pytest.raises(TypeError, match="Expected return type"):
        invalid_result()


def test_exception_retry_and_time_based_cache(monkeypatch, capsys):
    @decorators.exception_handler_decorator
    def explode():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        explode()
    assert "An error occurred" in capsys.readouterr().out

    attempts = {"count": 0}
    monkeypatch.setattr(decorators.time, "sleep", lambda _delay: None)

    @decorators.retry_decorator(max_retries=3, delay=0)
    def eventually_succeeds():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("retry")
        return "ok"

    assert eventually_succeeds() == "ok"
    assert attempts["count"] == 3

    @decorators.retry_decorator(max_retries=2, delay=0)
    def always_fails():
        raise RuntimeError("no")

    with pytest.raises(Exception, match="failed after 2 attempts"):
        always_fails()

    clock = {"now": 0.0}
    monkeypatch.setattr(decorators.time, "time", lambda: clock["now"])
    cache_calls = []

    @decorators.time_based_cache(expiration_time=10)
    def compute(value):
        cache_calls.append(value)
        return len(cache_calls)

    assert compute("x") == 1
    clock["now"] = 5.0
    assert compute("x") == 1
    clock["now"] = 11.0
    assert compute("x") == 2
