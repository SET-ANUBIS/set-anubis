from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "setanubis"))

project = "SET-ANUBIS"
author = "SET-ANUBIS contributors"
copyright = f"{date.today().year}, {author}"
version = release = "1.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
]

try:
    import sphinx_rtd_theme  # noqa: F401
    extensions.insert(0, "sphinx_rtd_theme")
    html_theme = "sphinx_rtd_theme"
except Exception:
    html_theme = "alabaster"

master_doc = "index"
source_suffix = ".rst"
templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "api/core*.rst",
    "api/examples.rst",
    "api/modules.rst",
    "api/test.rst",
    "dependencies.rst",
]
pygments_style = "sphinx"
html_static_path = ["_static"]
html_title = "SET-ANUBIS documentation"
html_short_title = "SET-ANUBIS"

nitpicky = False
autodoc_typehints = "description"
