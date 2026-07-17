"""Capture, summarize, and export intermediate selection stages."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd


def _slug(name: str) -> str:
    """Return a stable column-friendly name for a selection stage."""
    value = re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_")
    return value or "stage"


def _json_safe(value: Any) -> Any:
    """Convert pandas and NumPy values into JSON-compatible Python objects."""
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return None
        return value
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, np.ndarray, pd.Index)):
        return [_json_safe(item) for item in value]
    if pd.isna(value):
        return None
    return str(value)


@dataclass
class SelectionTrace:
    """Intermediate DataFrames and candidate/event summaries for one selection run.

    The stage DataFrames are available directly through ``stage_dataframes`` for
    interactive analysis.  ``write_report`` creates a compact JSON summary and a
    standalone HTML page without external JavaScript or CSS dependencies.
    """

    stage_dataframes: dict[str, pd.DataFrame]
    cut_flow: dict[str, float | int]
    candidate_summary: pd.DataFrame
    event_summary: pd.DataFrame

    @classmethod
    def from_stages(
        cls,
        stage_dataframes: Mapping[str, pd.DataFrame],
        cut_flow: Mapping[str, float | int],
    ) -> "SelectionTrace":
        """Build summaries from ordered, progressively selected DataFrames."""
        frames = {
            str(name): dataframe.copy(deep=True)
            for name, dataframe in stage_dataframes.items()
        }
        candidate_summary = cls._build_candidate_summary(frames)
        event_summary = cls._build_event_summary(candidate_summary, list(frames))
        return cls(
            stage_dataframes=frames,
            cut_flow=dict(cut_flow),
            candidate_summary=candidate_summary,
            event_summary=event_summary,
        )

    @staticmethod
    def _build_candidate_summary(
        stage_dataframes: Mapping[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """Create one row per original LLP candidate with pass/fail flags."""
        if not stage_dataframes:
            return pd.DataFrame()

        stage_names = list(stage_dataframes)
        original = stage_dataframes[stage_names[0]]
        summary = pd.DataFrame(index=original.index.copy())
        summary.index.name = original.index.name or "candidate_index"
        summary.insert(0, "candidate_index", original.index.tolist())

        for column in ("eventNumber", "weight", "pdgid", "status"):
            if column in original.columns:
                summary[column] = original[column].to_numpy(copy=True)

        stage_columns: list[tuple[str, str]] = []
        for stage_name, frame in stage_dataframes.items():
            column = f"passed_{_slug(stage_name)}"
            summary[column] = summary.index.isin(frame.index)
            stage_columns.append((stage_name, column))

        def last_passed(row: pd.Series) -> str | None:
            passed = [name for name, column in stage_columns if bool(row[column])]
            return passed[-1] if passed else None

        def first_failed(row: pd.Series) -> str | None:
            for name, column in stage_columns[1:]:
                if not bool(row[column]):
                    return name
            return None

        # pandas 3 infers the dedicated string dtype for mixed ``str``/``None``
        # results and converts missing values to ``NaN``.  These report columns
        # intentionally expose Python ``None`` for candidates without a failed
        # stage, so construct explicit object-dtype Series for a stable public
        # contract across pandas 2 and 3.
        summary["last_passed_stage"] = pd.Series(
            (last_passed(row) for _, row in summary.iterrows()),
            index=summary.index,
            dtype=object,
        )
        summary["first_failed_stage"] = pd.Series(
            (first_failed(row) for _, row in summary.iterrows()),
            index=summary.index,
            dtype=object,
        )
        return summary.reset_index(drop=True)

    @staticmethod
    def _build_event_summary(
        candidate_summary: pd.DataFrame,
        stage_names: list[str],
    ) -> pd.DataFrame:
        """Aggregate candidate pass/fail information by event number."""
        if candidate_summary.empty:
            return pd.DataFrame()

        event_column = (
            "eventNumber"
            if "eventNumber" in candidate_summary.columns
            else "candidate_index"
        )
        rows: list[dict[str, Any]] = []
        for event_number, group in candidate_summary.groupby(event_column, sort=True):
            row: dict[str, Any] = {
                "eventNumber": event_number,
                "n_candidates": int(len(group)),
            }
            last_stage: str | None = None
            for stage_name in stage_names:
                column = f"passed_{_slug(stage_name)}"
                count = int(group[column].sum())
                row[f"n_{_slug(stage_name)}"] = count
                row[column] = bool(count)
                if count:
                    last_stage = stage_name
            row["last_passed_stage"] = last_stage
            rows.append(row)
        return pd.DataFrame(rows)

    def to_dict(self, *, include_stage_records: bool = False) -> dict[str, Any]:
        """Return a JSON-compatible report dictionary."""
        stages: list[dict[str, Any]] = []
        for name, frame in self.stage_dataframes.items():
            stage: dict[str, Any] = {
                "name": name,
                "candidate_count": int(len(frame)),
                "event_count": int(frame["eventNumber"].nunique())
                if "eventNumber" in frame.columns
                else int(len(frame)),
                "weighted_count": float(frame["weight"].sum())
                if "weight" in frame.columns
                else None,
                "candidate_indices": [_json_safe(value) for value in frame.index],
            }
            if include_stage_records:
                stage["records"] = _json_safe(
                    frame.reset_index().to_dict(orient="records")
                )
            stages.append(stage)

        return {
            "cut_flow": _json_safe(self.cut_flow),
            "stages": stages,
            "candidates": _json_safe(self.candidate_summary.to_dict(orient="records")),
            "events": _json_safe(self.event_summary.to_dict(orient="records")),
        }

    def write_json(
        self,
        path: str | Path,
        *,
        include_stage_records: bool = False,
    ) -> Path:
        """Write the trace summary to JSON and return the output path."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                self.to_dict(include_stage_records=include_stage_records),
                indent=2,
                sort_keys=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return output

    def write_html(self, path: str | Path, *, title: str = "Selection trace") -> Path:
        """Write a standalone HTML report and return the output path."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict(include_stage_records=False)
        stage_cards = "".join(
            "<article><h3>{name}</h3><p>{candidates} candidates · "
            "{events} events · weighted {weighted}</p></article>".format(
                name=html.escape(str(stage["name"])),
                candidates=stage["candidate_count"],
                events=stage["event_count"],
                weighted=(
                    "n/a"
                    if stage["weighted_count"] is None
                    else f"{stage['weighted_count']:.6g}"
                ),
            )
            for stage in payload["stages"]
        )
        candidate_table = self.candidate_summary.to_html(
            index=False, border=0, classes="trace-table", escape=True
        )
        event_table = self.event_summary.to_html(
            index=False, border=0, classes="trace-table", escape=True
        )
        embedded_json = json.dumps(payload, separators=(",", ":")).replace(
            "<", "\\u003c"
        )
        document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2937; }}
h1, h2 {{ margin-top: 1.5rem; }}
.stage-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: .75rem; }}
article {{ border: 1px solid #d1d5db; border-radius: .5rem; padding: .75rem; background: #f9fafb; }}
article h3 {{ margin: 0 0 .4rem; }}
.trace-table {{ border-collapse: collapse; width: 100%; font-size: .88rem; display: block; overflow-x: auto; }}
.trace-table th, .trace-table td {{ border: 1px solid #d1d5db; padding: .35rem .5rem; white-space: nowrap; }}
.trace-table th {{ background: #f3f4f6; position: sticky; top: 0; }}
code {{ background: #f3f4f6; padding: .1rem .25rem; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p>The report records which LLP candidates and events survive each ordered selection stage.</p>
<h2>Stage overview</h2>
<section class="stage-grid">{stage_cards}</section>
<h2>Event summary</h2>
{event_table}
<h2>Candidate summary</h2>
{candidate_table}
<script id="selection-trace-data" type="application/json">{embedded_json}</script>
</body>
</html>
"""
        output.write_text(document, encoding="utf-8")
        return output

    def write_report(
        self,
        output_dir: str | Path,
        *,
        basename: str = "selection_trace",
        include_stage_records: bool = False,
        title: str = "Selection trace",
    ) -> tuple[Path, Path]:
        """Write matching JSON and HTML reports into ``output_dir``."""
        directory = Path(output_dir)
        json_path = self.write_json(
            directory / f"{basename}.json",
            include_stage_records=include_stage_records,
        )
        html_path = self.write_html(directory / f"{basename}.html", title=title)
        return json_path, html_path
