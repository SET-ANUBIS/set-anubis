from __future__ import annotations
import os
from typing import List, Dict, Any, Set

import pandas as pd

from SetAnubis.core.Selection.domain.Models import HepmcRef, IndexWriterConfig, IndexWriteResult
from SetAnubis.core.Selection.ports.output.IHepMCIndex import HepmcIndexPort


class PandasHepmcIndexWriterAdapter(HepmcIndexPort):

    def write_index(self, items: List[HepmcRef], cfg: IndexWriterConfig) -> IndexWriteResult:
        existing = self._safe_read(cfg.index_csv_path)

        selected_ids: Set[str] = {str(it.event_id) for it in items}

        already = set(existing["event_id"].astype(str)) if not existing.empty and "event_id" in existing.columns else set()
        fresh = [it for it in items if (str(it.event_id) not in already)] if cfg.dedupe_on_event_id else list(items)

        existing_selected = pd.DataFrame()
        if not existing.empty and "event_id" in existing.columns and selected_ids:
            existing_selected = existing[existing["event_id"].astype(str).isin(selected_ids)]

        if not fresh:
            return IndexWriteResult(
                added_rows=0,
                total_rows_after=int(existing.shape[0]) if existing is not None else 0,
                deduped_rows=len(items) - len(fresh),
                selected_df=existing_selected.copy() if not existing_selected.empty else pd.DataFrame()
            )

        df_new = self._to_df(fresh, cfg.extra_columns or {})

        if cfg.rewrite_in_one_go:
            updated = self._concat_and_reindex(existing, df_new)

            sel_mask = updated["event_id"].astype(str).isin(selected_ids) if "event_id" in updated.columns else pd.Series(False, index=updated.index)
            selected_df = updated.loc[sel_mask].copy()

            self._write(updated, cfg.index_csv_path)
            return IndexWriteResult(
                added_rows=int(df_new.shape[0]),
                total_rows_after=int(updated.shape[0]),
                deduped_rows=len(items) - len(fresh),
                selected_df=selected_df
            )
        else:
            start_idx = int(existing.index.max()) + 1 if not existing.empty else 0
            added = 0
            pos = 0

            if not os.path.exists(cfg.index_csv_path) and not existing.empty:
                self._write(existing, cfg.index_csv_path)

            selected_parts = []
            if not existing_selected.empty:
                selected_parts.append(existing_selected.copy())

            while pos < len(df_new):
                chunk = df_new.iloc[pos: pos + cfg.batch_size_rows].copy()
                chunk.index = range(start_idx, start_idx + len(chunk))
                start_idx += len(chunk)
                added += len(chunk)

                self._append(chunk, cfg.index_csv_path, header=(not os.path.exists(cfg.index_csv_path) and pos == 0))

                selected_parts.append(chunk)
                pos += len(chunk)

            if selected_parts:
                cols = sorted(set().union(*[set(p.columns) for p in selected_parts]))
                selected_parts = [p.reindex(columns=cols) for p in selected_parts]
                selected_df = pd.concat(selected_parts, axis=0)
            else:
                selected_df = pd.DataFrame()

            total = (0 if existing is None else int(existing.shape[0])) + added
            return IndexWriteResult(
                added_rows=added,
                total_rows_after=total,
                deduped_rows=len(items) - len(fresh),
                selected_df=selected_df
            )

    def _to_df(self, items: List[HepmcRef], extra_cols: Dict[str, Any]) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        for it in items:
            rows.append({
                "event_id": it.event_id,
                "model": it.model,
                "run_name": it.run_name,
                "hepmc_path": it.hepmc_path,
                "cross_section_pb": it.cross_section_pb,
                "scan_params": it.scan_params,
                "scan_widths": it.scan_widths,
                **extra_cols,
            })
        return pd.DataFrame(rows)

    def _safe_read(self, path: str) -> pd.DataFrame:
        if not os.path.exists(path):
            return pd.DataFrame()
        try:
            return pd.read_csv(path, index_col=0)
        except Exception:
            return pd.DataFrame()

    def _concat_and_reindex(self, existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
        if new is None or new.empty:
            return existing if existing is not None else pd.DataFrame()
        if existing is None or existing.empty:
            new = new.copy()
            new.index = range(0, len(new))
            return new
        start = int(existing.index.max()) + 1
        new = new.copy()
        new.index = range(start, start + len(new))
        cols = sorted(set(existing.columns).union(set(new.columns)))
        return pd.concat([existing.reindex(columns=cols), new.reindex(columns=cols)], axis=0)

    def _write(self, df: pd.DataFrame, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=True)

    def _append(self, df: pd.DataFrame, path: str, header: bool) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=True, mode="a", header=header)
