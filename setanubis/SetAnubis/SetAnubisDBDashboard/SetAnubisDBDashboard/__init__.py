"""Dash database monitor for SetAnubis event databases."""

__all__ = ["make_app"]

try:
    from .app import make_app
except Exception:  # Dash may not be installed while importing package metadata
    make_app = None
