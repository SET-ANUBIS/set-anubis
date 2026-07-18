"""Campaign provenance and compact-event-bundle inspector for SET-ANUBIS."""

from __future__ import annotations

from typing import Any

__all__ = ["make_app"]


def __getattr__(name: str) -> Any:
    """Load the optional Dash application lazily.

    Delaying the import keeps package metadata and ``python -m ...app`` usage
    free from Dash side effects while preserving ``from ... import make_app``.
    """
    if name == "make_app":
        from .app import make_app

        return make_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
