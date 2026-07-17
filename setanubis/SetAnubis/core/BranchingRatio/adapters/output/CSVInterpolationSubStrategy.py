"""CSV-backed interpolation strategy for decay widths and branching ratios."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

import numpy as np
from scipy.interpolate import LinearNDInterpolator

from SetAnubis.core.BranchingRatio.ports.IFileInterpolationStrategy import (
    IFileInterpolationSubStrategy,
)
from SetAnubis.core.Common.MultiSet import MultiSet


class CSVInterpolationSubStrategy(IFileInterpolationSubStrategy):
    """Linearly interpolate channel values over one or more model parameters."""

    def __init__(self) -> None:
        self._data: list[dict[str, str]] = []
        self._varying_params: list[str] = []
        self._is_br = False

    def load_file(
        self,
        file_path: str,
        varying_params: List[str],
        is_br: bool = False,
    ) -> None:
        """Load a CSV table and validate its parameter columns."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        self._varying_params = list(varying_params)
        self._is_br = bool(is_br)
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = set(reader.fieldnames or [])
            missing = [name for name in self._varying_params if name not in fieldnames]
            if missing:
                raise ValueError(f"CSV table is missing parameter columns: {missing}")
            self._data = list(reader)
        if not self._data:
            raise ValueError(f"CSV table is empty: {path}")

    def interpolate(
        self,
        mother: int,
        daughters: MultiSet[int],
        param_values: Dict[str, float],
    ) -> float:
        """Interpolate one channel at the requested model-parameter point."""
        missing = [name for name in self._varying_params if name not in param_values]
        if missing:
            raise ValueError(f"Missing interpolation parameters: {missing}")

        daughters_str = ";".join(str(value) for value in sorted(daughters))
        column = f"{mother}:{daughters_str}"
        if column not in self._data[0]:
            raise KeyError(
                f"No column {column!r} in CSV table; available columns are "
                f"{list(self._data[0])}"
            )

        points = np.asarray(
            [
                [float(row[name]) for name in self._varying_params]
                for row in self._data
            ],
            dtype=float,
        )
        values = np.asarray([float(row[column]) for row in self._data], dtype=float)
        query = np.asarray([float(param_values[name]) for name in self._varying_params])

        exact = np.all(np.isclose(points, query, rtol=0.0, atol=1e-12), axis=1)
        if exact.any():
            return float(values[np.flatnonzero(exact)[0]])

        if points.shape[1] == 1:
            order = np.argsort(points[:, 0])
            coordinates = points[order, 0]
            if query[0] < coordinates[0] or query[0] > coordinates[-1]:
                raise ValueError("Interpolation point lies outside the CSV parameter range")
            return float(np.interp(query[0], coordinates, values[order]))

        interpolator = LinearNDInterpolator(points, values, fill_value=np.nan)
        result = float(np.asarray(interpolator(query)).reshape(-1)[0])
        if np.isnan(result):
            raise ValueError("Interpolation point lies outside the CSV parameter grid")
        return result
