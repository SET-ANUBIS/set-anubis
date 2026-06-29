"""Backward-compatible access to the public SetAnubis interfaces.

This module intentionally avoids ``from SetAnubis import *``.  Importing every
public object at module import time can create circular imports inside the core,
for example when MadGraph's command-card classes import ``SetAnubisInterface``
while the public API is still resolving ``GeneralCardInterface``.

New user code should prefer ``from setanubis import ...``.  Internal modules that
still import from ``SetAnubis.core.interfaces`` get the same lazy public objects
without eagerly importing unrelated subsystems.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from SetAnubis import _EXPORTS as _PUBLIC_EXPORTS  # private but stable in-package map
from SetAnubis import __version__, asset_path, assets_dir, repository_root, ufo_path

__all__ = [
    "__version__",
    "asset_path",
    "assets_dir",
    "repository_root",
    "ufo_path",
    *_PUBLIC_EXPORTS.keys(),
]


def __getattr__(name: str) -> Any:
    target = _PUBLIC_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'SetAnubis.core.interfaces' has no attribute {name!r}")

    if isinstance(target, tuple):
        module_name, attr_name = target
    else:
        module_name, attr_name = target, name

    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
