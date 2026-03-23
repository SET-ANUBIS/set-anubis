from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd

C_LIGHT_M_S = 299_792_458.0


def _call_or_attr(obj, name: str) -> float:
    """Return an attribute value as a float, calling it if needed."""
    v = getattr(obj, name)
    return float(v() if callable(v) else v)


def _vertex_xyzt(vtx: object) -> Optional[Tuple[float, float, float, float]]:
    """Extract a vertex position as ``(x, y, z, t)``.

    For HepMC vertex positions, the time-like component is interpreted as
    ``c*t`` and therefore carries the same length unit as ``x``, ``y`` and
    ``z``.
    """
    if vtx is None:
        return None

    pos = getattr(vtx, "position", None)
    try:
        if pos is not None:
            return (
                _call_or_attr(pos, "x"),
                _call_or_attr(pos, "y"),
                _call_or_attr(pos, "z"),
                _call_or_attr(pos, "t"),
            )
    except Exception:
        pass

    try:
        return (
            _call_or_attr(vtx, "x"),
            _call_or_attr(vtx, "y"),
            _call_or_attr(vtx, "z"),
            _call_or_attr(vtx, "t"),
        )
    except Exception:
        return None


def add_lifetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` enriched with HNL lifetime columns.

    Required input columns are:
    - ``prod_x_m``, ``prod_y_m``, ``prod_z_m``
    - ``dec_x_m``, ``dec_y_m``, ``dec_z_m``
    - ``prod_ct_m``, ``dec_ct_m``

    Produced columns are:
    - ``ct_lab_m``
    - ``ctau_m``
    - ``lifetime_lab_s`` / ``lifetime_lab_ns``
    - ``lifetime_proper_s`` / ``lifetime_proper_ns``
    """
    out = df.copy()

    needed = [
        "prod_x_m", "prod_y_m", "prod_z_m",
        "dec_x_m", "dec_y_m", "dec_z_m",
        "prod_ct_m", "dec_ct_m",
    ]
    if any(col not in out.columns for col in needed):
        for col in ["ct_lab_m", "ctau_m", "lifetime_lab_s", "lifetime_lab_ns", "lifetime_proper_s", "lifetime_proper_ns"]:
            if col not in out.columns:
                out[col] = np.nan
        return out

    dx = pd.to_numeric(out["dec_x_m"], errors="coerce") - pd.to_numeric(out["prod_x_m"], errors="coerce")
    dy = pd.to_numeric(out["dec_y_m"], errors="coerce") - pd.to_numeric(out["prod_y_m"], errors="coerce")
    dz = pd.to_numeric(out["dec_z_m"], errors="coerce") - pd.to_numeric(out["prod_z_m"], errors="coerce")
    dct = pd.to_numeric(out["dec_ct_m"], errors="coerce") - pd.to_numeric(out["prod_ct_m"], errors="coerce")

    finite = np.isfinite(dx) & np.isfinite(dy) & np.isfinite(dz) & np.isfinite(dct)
    forward = dct >= 0.0

    ct_lab = np.where(finite & forward, dct, np.nan)
    interval2 = dct * dct - dx * dx - dy * dy - dz * dz
    ctau = np.where(finite & forward & np.isfinite(interval2) & (interval2 >= 0.0), np.sqrt(np.maximum(interval2, 0.0)), np.nan)

    out["ct_lab_m"] = ct_lab.astype(float)
    out["ctau_m"] = ctau.astype(float)
    out["lifetime_lab_s"] = out["ct_lab_m"] / C_LIGHT_M_S
    out["lifetime_lab_ns"] = 1.0e9 * out["lifetime_lab_s"]
    out["lifetime_proper_s"] = out["ctau_m"] / C_LIGHT_M_S
    out["lifetime_proper_ns"] = 1.0e9 * out["lifetime_proper_s"]
    return out


def lifetime_column_for_mode(mode: str, unit: str = "ns") -> str:
    mode_key = "lab" if str(mode).lower() == "lab" else "proper"
    unit_key = "s" if str(unit).lower() == "s" else "ns"
    return f"lifetime_{mode_key}_{unit_key}"


def event_lifetime_column_for_mode(mode: str, unit: str = "ns") -> str:
    mode_key = "lab" if str(mode).lower() == "lab" else "proper"
    unit_key = "s" if str(unit).lower() == "s" else "ns"
    return f"lifetime_{mode_key}_{unit_key}_max"


def lifetime_label_for_mode(mode: str, unit: str = "ns") -> str:
    unit_key = "s" if str(unit).lower() == "s" else "ns"
    if str(mode).lower() == "lab":
        return f"HNL lifetime (lab) [{unit_key}]"
    return f"HNL lifetime (proper) [{unit_key}]"
