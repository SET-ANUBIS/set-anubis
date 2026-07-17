"""Reusable decorators for timing, logging, validation, retries, and caching."""

from __future__ import annotations

import logging
from functools import wraps
from time import monotonic, perf_counter, sleep
from typing import Any, Callable, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])
LOGGER = logging.getLogger(__name__)


def timing_decorator(func: F) -> F:
    """Print the elapsed wall-clock duration of a function call."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = perf_counter()
        result = func(*args, **kwargs)
        elapsed_time = perf_counter() - start_time
        print(f"Function {func.__name__} took {elapsed_time:.4f} seconds to complete.")
        return result

    return cast(F, wrapper)


def log_decorator(func: F) -> F:
    """Log a function call and its returned value at debug level."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        LOGGER.debug(
            "Calling function %s with args: %s, kwargs: %s",
            func.__name__,
            args,
            kwargs,
        )
        result = func(*args, **kwargs)
        LOGGER.debug("Function %s returned %r", func.__name__, result)
        return result

    return cast(F, wrapper)


def validate_inputs(expected_types: tuple[type, ...]) -> Callable[[F], F]:
    """Validate positional argument types before calling the wrapped function."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for arg, expected_type in zip(args, expected_types):
                if not isinstance(arg, expected_type):
                    raise TypeError(
                        f"Expected type {expected_type} but got {type(arg)}"
                    )
            return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


def _cache_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, ...]:
    """Build a deterministic cache key from positional and keyword arguments."""

    return args + (("__kwargs__", tuple(sorted(kwargs.items()))),)


def memoize(func: F) -> F:
    """Cache function results by positional and keyword arguments."""

    cache: dict[tuple[Any, ...], Any] = {}

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        key = _cache_key(args, kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return cast(F, wrapper)


def exception_handler_decorator(func: F) -> F:
    """Print contextual information before re-raising a function exception."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            print(f"An error occurred in function {func.__name__}: {exc}")
            raise

    return cast(F, wrapper)


def tracing_decorator(func: F) -> F:
    """Print function entry, arguments, result, and exit."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(
            f"Entering {func.__name__} with arguments: {args} "
            f"and keyword arguments: {kwargs}"
        )
        result = func(*args, **kwargs)
        print(f"Exiting {func.__name__} with result: {result}")
        return result

    return cast(F, wrapper)


def retry_decorator(
    max_retries: int = 3,
    delay: float = 1,
) -> Callable[[F], F]:
    """Retry a failed function call up to ``max_retries`` times."""

    if max_retries < 1:
        raise ValueError("max_retries must be at least 1")
    if delay < 0:
        raise ValueError("delay must be non-negative")

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    print(f"Attempt {attempt} failed: {exc}")
                    if attempt < max_retries:
                        sleep(delay)
            raise RuntimeError(
                f"Function {func.__name__} failed after {max_retries} attempts."
            )

        return cast(F, wrapper)

    return decorator


def time_based_cache(expiration_time: float = 60) -> Callable[[F], F]:
    """Cache function results until ``expiration_time`` seconds have elapsed."""

    if expiration_time < 0:
        raise ValueError("expiration_time must be non-negative")

    def decorator(func: F) -> F:
        cache: dict[tuple[Any, ...], Any] = {}
        cache_time: dict[tuple[Any, ...], float] = {}

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = _cache_key(args, kwargs)
            current_time = monotonic()
            if key in cache and current_time - cache_time[key] < expiration_time:
                return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            cache_time[key] = current_time
            return result

        return cast(F, wrapper)

    return decorator


def return_type_checker(expected_type: type) -> Callable[[F], F]:
    """Ensure that a wrapped function returns an instance of ``expected_type``."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            if not isinstance(result, expected_type):
                raise TypeError(
                    f"Expected return type {expected_type}, but got {type(result)}"
                )
            return result

        return cast(F, wrapper)

    return decorator
