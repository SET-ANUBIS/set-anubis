"""Shared runtime helpers for executable SET-ANUBIS examples.

The example modules remain import-safe so they can be inspected, documented and
tested without starting optional external workflows.  When an example is
executed as a script, :func:`run_example_entrypoint` displays the project banner
once and then calls its ``main`` function.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from SetAnubis.branding import show_banner


def run_example_entrypoint(main: Callable[[], Any]) -> int:
    """Display the SET-ANUBIS banner and execute an example entry point.

    Parameters
    ----------
    main:
        Zero-argument callable implementing the example.  ``None`` is treated as
        a successful exit, while integer return values are preserved.

    Returns
    -------
    int
        Process-compatible exit status.
    """

    show_banner(force=True)
    result = main()
    return 0 if result is None else int(result)
