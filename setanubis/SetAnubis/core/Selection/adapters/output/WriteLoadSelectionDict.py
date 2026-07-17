"""Backward-compatible helpers for trusted selection bundle persistence."""

from __future__ import annotations

from os import PathLike
from typing import Dict

import pandas as pd

from SetAnubis.core.Selection.domain.DatasetSource import BundleIO


def save_bundle(
    bundle: Dict[str, pd.DataFrame], filepath: str | PathLike[str]
) -> None:
    """Save a selection bundle as a gzip-compressed pickle file.

    The extension is not used to select the compression format; ``.pkl`` and
    ``.pkl.gz`` are both accepted for compatibility.  Only load trusted files.
    """
    BundleIO.save_bundle(bundle, filepath)


def load_bundle(filepath: str | PathLike[str]) -> Dict[str, pd.DataFrame]:
    """Load a trusted selection bundle, detecting gzip from its file header."""
    return BundleIO.load_bundle(filepath)
