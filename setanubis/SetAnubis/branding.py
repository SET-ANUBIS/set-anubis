"""Console branding helpers for the public SET-ANUBIS API.

The banner is intentionally small, emitted at most once per Python process, and
can be controlled through the ``SETANUBIS_BANNER`` environment variable:

``auto`` (default)
    Display the banner only when writing to an interactive terminal.
``always``
    Display the banner even when stdout is redirected.
``never``
    Disable the banner.
"""

from __future__ import annotations

import os
import sys
import threading
from typing import TextIO

from SetAnubis._version import __version__

_BANNER_LOCK = threading.Lock()
_BANNER_SHOWN = False


def _pythia_binding_status() -> str:
    """Return a concise status for the optional compiled Pythia binding."""

    try:
        from SetAnubis.core.Pythia.domain.PythiaRunManager import (
            check_pythia_binding,
        )

        report = check_pythia_binding()
    except Exception:
        return "unavailable (CMND generation remains available)"

    if report.get("available"):
        module = report.get("module") or "pythia_sim"
        return f"available ({module})"
    return "unavailable (CMND generation remains available)"


def _zenodo_citation_text() -> str:
    """Return the Zenodo citation label, optionally including a known DOI."""

    doi = os.getenv("SETANUBIS_ZENODO_DOI", "").strip()
    if doi:
        return f"Zenodo {doi}"
    return "the matching SET-ANUBIS Zenodo software release"


def _banner_text() -> str:
    return (
        "------------------------------------------------------------------------\n"
        f" SET-ANUBIS {__version__}\n"
        " Simulation, accEptance and sensiTivity studies framework for ANUBIS\n"
        " Developers: Théo Reymermier (lead) and Paul Swallow\n"
        " Contact: anubis-active@cern.ch\n"
        f" Pythia binding: {_pythia_binding_status()}\n"
        " Cite: ANUBIS proceedings contribution, arXiv:2512.14942\n"
        f"       and {_zenodo_citation_text()}\n"
        " https://github.com/SET-ANUBIS/set-anubis\n"
        "------------------------------------------------------------------------"
    )


def _normalise_mode(value: str | None) -> str:
    mode = (value or "auto").strip().lower()
    aliases = {
        "1": "always",
        "true": "always",
        "yes": "always",
        "on": "always",
        "0": "never",
        "false": "never",
        "no": "never",
        "off": "never",
        "quiet": "never",
    }
    mode = aliases.get(mode, mode)
    return mode if mode in {"auto", "always", "never"} else "auto"


def show_banner(*, force: bool = False, stream: TextIO | None = None) -> bool:
    """Display the SET-ANUBIS console banner at most once per process.

    Parameters
    ----------
    force:
        Ignore the automatic terminal detection. The ``never`` environment mode
        still takes precedence, so users can always silence library output.
    stream:
        Text stream receiving the banner. Defaults to :data:`sys.stdout`.

    Returns
    -------
    bool
        ``True`` when the banner was emitted by this call.
    """

    global _BANNER_SHOWN

    output = stream or sys.stdout
    mode = _normalise_mode(os.getenv("SETANUBIS_BANNER"))
    if mode == "never":
        return False
    if not force and mode == "auto" and not bool(getattr(output, "isatty", lambda: False)()):
        return False

    with _BANNER_LOCK:
        if _BANNER_SHOWN:
            return False
        print(_banner_text(), file=output)
        _BANNER_SHOWN = True
        return True


def _reset_banner_state_for_tests() -> None:
    """Reset the process-level state for isolated unit tests."""

    global _BANNER_SHOWN
    with _BANNER_LOCK:
        _BANNER_SHOWN = False
