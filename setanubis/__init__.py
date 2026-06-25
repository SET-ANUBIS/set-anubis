"""Source-tree compatibility wrapper for the public :mod:`setanubis` API.

The installable distribution exposes a top-level ``setanubis`` module from
``setanubis.py``.  When running directly from a checkout, the repository layout
also contains a directory named ``setanubis``; this wrapper prevents that
directory from shadowing the public API while preserving lazy imports.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from . import setanubis as _public  # noqa: E402

__version__ = _public.__version__
asset_path = _public.asset_path
assets_dir = _public.assets_dir
repository_root = _public.repository_root
ufo_path = _public.ufo_path
__all__ = _public.__all__


def __getattr__(name: str):
    value = getattr(_public, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return _public.__dir__()
