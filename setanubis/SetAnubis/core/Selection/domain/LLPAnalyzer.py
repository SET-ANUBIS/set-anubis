from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Iterable, Optional
import ast
import math
import numpy as np
import pandas as pd


class PhysicsUtils:
    @staticmethod
    def pt(x: np.ndarray | float, y: np.ndarray | float) -> np.ndarray | float:
        return np.hypot(x, y)


@dataclass(frozen=True)
class Schema:
    required: Tuple[str, ...] = (
        "eventNumber", "particleIndex", "px", "py", "pt", "status", "PID",
        "charge", "nChildren", "childrenIndices", "prodVertexDist"
    )

    @staticmethod
    def ensure(df: pd.DataFrame) -> None:
        missing = [c for c in Schema.required if c not in df.columns]
        if missing:
            raise ValueError(f"Columns missing in df: {missing}")


class EventGraph:
    """Memory-efficient graph lookup over one HepMC dataframe.

    The public API is intentionally identical to the historical implementation
    (``row_of``, ``children_of``, ``pid_of`` and ``nchildren_of``), so the
    selection physics and traversal order are unchanged.

    Historically SET-ANUBIS materialised four Python dictionaries with one
    ``(eventNumber, particleIndex)`` key per particle.  On showered HepMC files
    that representation dominates memory.  The implementation below keeps the
    source columns as NumPy views and stores only:

    * one sorted row-position array;
    * one sorted particle-index array; and
    * one small event -> slice dictionary (one entry per event, not particle).

    A particle lookup is then a binary search inside the corresponding event.
    Duplicate ``(event, particleIndex)`` pairs retain the old behaviour: the
    last dataframe row wins.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        Schema.ensure(df)
        self.df = df

        # Column views: these normally share the dataframe's underlying storage
        # and therefore do not duplicate the full HepMC table.
        self._event_values = df["eventNumber"].to_numpy(dtype=np.int64, copy=False)
        self._pidx_values = df["particleIndex"].to_numpy(dtype=np.int64, copy=False)
        self._pid_values = df["PID"].to_numpy(copy=False)
        self._nchildren_values = df["nChildren"].to_numpy(copy=False)
        self._children_values = df["childrenIndices"].to_numpy(copy=False)
        # Keep the existing pandas Index object by reference; converting a
        # RangeIndex to NumPy would allocate another O(N) integer array.
        self._row_index_labels = df.index

        n_rows = len(df)
        if n_rows == 0:
            self._lookup_order = np.empty(0, dtype=np.intp)
            self._lookup_pidx = np.empty(0, dtype=np.int64)
            self._event_slices: Dict[int, Tuple[int, int]] = {}
            return

        # Sort by event, then particleIndex, then original row position.  The
        # final key means that searchsorted(..., side="right") reproduces the
        # previous dict-comprehension semantics for duplicate particle keys.
        positions = np.arange(n_rows, dtype=np.intp)
        order = np.lexsort((positions, self._pidx_values, self._event_values))
        sorted_events = self._event_values[order]

        self._lookup_order = order
        self._lookup_pidx = self._pidx_values[order]

        # Only one Python dict entry per event.  ``sorted_events`` is temporary
        # and can be released after the slices have been constructed.
        starts = np.flatnonzero(
            np.r_[True, sorted_events[1:] != sorted_events[:-1]]
        )
        ends = np.r_[starts[1:], n_rows]
        self._event_slices = {
            int(sorted_events[start]): (int(start), int(end))
            for start, end in zip(starts, ends)
        }

    @staticmethod
    def _to_list(value) -> List[int]:
        """Parse ``childrenIndices`` exactly like the historical graph."""
        if isinstance(value, list):
            return list(value)
        if isinstance(value, str):
            try:
                parsed = ast.literal_eval(value)
                return list(parsed) if isinstance(parsed, list) else []
            except Exception:
                return []
        return []

    def _position_of(self, event: int, pidx: int) -> Optional[int]:
        """Return the positional dataframe row for ``(event, particleIndex)``."""
        span = self._event_slices.get(int(event))
        if span is None:
            return None

        start, end = span
        block = self._lookup_pidx[start:end]
        if block.size == 0:
            return None

        # ``right - 1`` intentionally selects the last duplicate key, matching
        # ``{key: value for ...}`` from the previous implementation.
        rel = int(np.searchsorted(block, int(pidx), side="right")) - 1
        if rel < 0 or int(block[rel]) != int(pidx):
            return None
        return int(self._lookup_order[start + rel])

    def row_of(self, event: int, pidx: int) -> Optional[int]:
        pos = self._position_of(event, pidx)
        if pos is None:
            return None
        return int(self._row_index_labels[pos])

    def children_of(self, event: int, pidx: int) -> List[int]:
        pos = self._position_of(event, pidx)
        if pos is None:
            return []
        return self._to_list(self._children_values[pos])

    def pid_of(self, event: int, pidx: int) -> int:
        pos = self._position_of(event, pidx)
        if pos is None:
            return 0
        return int(self._pid_values[pos])

    def nchildren_of(self, event: int, pidx: int) -> int:
        pos = self._position_of(event, pidx)
        if pos is None:
            return 0
        value = self._nchildren_values[pos]
        return int(value) if not pd.isna(value) else 0


# Hunter (iterative DFS without recursion)
class ChildrenHunter:
    def __init__(self, graph: EventGraph, llp_pids):
        self.g = graph
        self.llp_pids = set(int(p) for p in llp_pids)

    def hunt(self, event: int, particle_index: int) -> list[int]:
        """
        If children is identical LLP (from parent and parent has nChildren==1) then we doesn't add it and doesn't go further (like Paul's script with continu)
        """
        out: list[int] = []
        seen: set[int] = set()

        parent_pid0 = self.g.pid_of(event, particle_index)
        parent_nc0 = self.g.nchildren_of(event, particle_index)

        # Stack for exploration (child_idx, parent_pid, parent_nc)
        stack: list[tuple[int, int, int]] = [
            (c, parent_pid0, parent_nc0) for c in self.g.children_of(event, particle_index)
        ]

        while stack:
            child_idx, parent_pid_cur, parent_nc_cur = stack.pop()
            if child_idx in seen:
                continue
            seen.add(child_idx)

            child_pid = self.g.pid_of(event, child_idx)

            # Skip identical LLP -> LLP
            skip_child = (
                (child_pid in self.llp_pids) and
                (parent_pid_cur in self.llp_pids) and
                (child_pid == parent_pid_cur) and
                (parent_nc_cur == 1)
            )

            if skip_child:
                continue

            out.append(child_idx)
            child_nc = self.g.nchildren_of(event, child_idx)
            for gc in self.g.children_of(event, child_idx):
                stack.append((gc, child_pid, child_nc))

        return out


class LLPAnalyzer:
    """
    API for launching the Dict[str->df] creation from a DataFrame using the above Graph.
    """
    def __init__(self, df: pd.DataFrame, pt_min_cfg: Dict[str, float]) -> None:
        Schema.ensure(df)
        # Keep the source dataframe by reference.  All returned dataframes that
        # are mutated later (LLPs / LLPchildren) are explicitly copied below, so
        # duplicating the complete HepMC table here is unnecessary.
        self.df = df
        self.pt_min_cfg = dict(pt_min_cfg)
        self.graph = EventGraph(self.df)

    # Atomic selections.
    def select_final_states(self) -> pd.DataFrame:
        return self.df[(self.df["nChildren"] == 0) & (self.df["status"] == 1)]

    def select_llps(self, llpid: int) -> pd.DataFrame:
        return self.df[self.df["PID"] == int(llpid)]

    def select_prompt(self, df: pd.DataFrame, max_dist_mm: float = 10.0) -> pd.DataFrame:
        return df[df["prodVertexDist"] < max_dist_mm]

    def select_neutrinos(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[df["PID"].isin([12, 14, 16, 18])]

    def _build_llp_children(self, llpid: int) -> Tuple[pd.DataFrame, List[int]]:
        """
        Construct LLPchildren (df index like the original df) and keep the index of the original df
        """
        llp_rows = self.select_llps(llpid)
        hunter = ChildrenHunter(self.graph, llp_pids=[llpid])

        #nice optimisation here -> no concat in loop, stocking pairs and do in one time after.
        child_df_indices: List[int] = []
        originating_llp_df_indices: List[int] = []

        for llp_df_idx in llp_rows.index.to_list():
            ev = int(self.df.at[llp_df_idx, "eventNumber"])
            pidx = int(self.df.at[llp_df_idx, "particleIndex"])
            child_particle_indices = hunter.hunt(ev, pidx)
            if not child_particle_indices:
                continue

            # (event, child_particle_idx) -> row index Pandas
            mapped = [self.graph.row_of(ev, cpi) for cpi in child_particle_indices]
            mapped = [m for m in mapped if m is not None]

            child_df_indices.extend(mapped)
            originating_llp_df_indices.extend([int(llp_df_idx)] * len(mapped))

        if not child_df_indices:
            # Empty df (right)
            return self.df.iloc[[]], []

        llp_children = self.df.loc[child_df_indices].copy()
        llp_children["LLPindex"] = originating_llp_df_indices
        llp_children = llp_children[llp_children["PID"] != int(llpid)]
        llp_children = llp_children[~llp_children.index.duplicated(keep="first")]

        return llp_children, originating_llp_df_indices

    def _compute_event_met(self, final_states_no_llp: pd.DataFrame) -> pd.DataFrame:
        # Sum of px/py by event
        sums = final_states_no_llp.groupby("eventNumber")[["px", "py"]].sum()
        sums.rename(columns={"px": "METx", "py": "METy"}, inplace=True)
        sums["MET"] = PhysicsUtils.pt(sums["METx"].to_numpy(), sums["METy"].to_numpy())
        return sums


    def create_selection_working_set(self, llpid: int) -> Dict[str, pd.DataFrame]:
        """Build only the temporary frames required before SelectionEngine.

        This method is physics-equivalent to ``create_sample_dataframes`` for
        the selection path, but deliberately avoids materialising the large
        diagnostic/intermediate frames ``finalStates``, ``finalStates_NoLLP``
        and ``finalStates_Neutrinos``.

        The returned charged/neutral frames contain only columns consumed by
        JetBuilder/IsolationComputer.  After jets and minDeltaR are computed,
        SelectionPipeline can discard them and keep only ``LLPs`` and
        ``LLPchildren``.
        """
        llp_children, _originating_llp = self._build_llp_children(llpid)

        llps_all = self.select_llps(llpid).copy()
        if len(llp_children):
            keep_llp_idx = set(llp_children["LLPindex"].tolist())
            llps = llps_all[
                (llps_all.index.isin(keep_llp_idx)) | (llps_all["status"] == 1)
            ].copy()
        else:
            llps = llps_all[llps_all["status"] == 1].copy()

        # Reproduce exactly the masks used by create_sample_dataframes without
        # creating full-width copies for every intermediate final-state table.
        final_mask = (self.df["nChildren"] == 0) & (self.df["status"] == 1)
        if len(llp_children):
            child_mask = self.df.index.isin(llp_children.index)
            final_mask = final_mask & (~child_mask)
        final_mask = final_mask & (self.df["PID"] != int(llpid))

        non_nu_mask = final_mask & (~self.df["PID"].isin([12, 14, 16, 18]))

        # MET uses precisely the non-neutrino, non-LLP final states used by the
        # historical implementation.
        if not llps.empty:
            met_input = self.df.loc[non_nu_mask, ["eventNumber", "px", "py"]]
            met_by_event = self._compute_event_met(met_input)
            llps["METx"] = llps["eventNumber"].map(met_by_event["METx"]).fillna(0.0).to_numpy()
            llps["METy"] = llps["eventNumber"].map(met_by_event["METy"]).fillna(0.0).to_numpy()
            llps["MET"] = PhysicsUtils.pt(llps["METx"].to_numpy(), llps["METy"].to_numpy())
        else:
            llps["METx"] = []
            llps["METy"] = []
            llps["MET"] = []

        charge = self.df["charge"]
        prompt = self.df["prodVertexDist"] < 10.0
        charged_mask = (
            non_nu_mask
            & (charge != 0)
            & (charge != None)
            & prompt
            & (self.df["pt"] > float(self.pt_min_cfg.get("chargedTrack", 0.0)))
        )
        neutral_mask = non_nu_mask & (charge == 0) & prompt

        charged_cols = [
            c for c in (
                "eventNumber", "px", "py", "pz", "E", "pt", "eta", "phi", "weight"
            ) if c in self.df.columns
        ]
        neutral_cols = [
            c for c in (
                "eventNumber", "px", "py", "pz", "E", "weight"
            ) if c in self.df.columns
        ]

        charged = self.df.loc[charged_mask, charged_cols].copy()
        neutral = self.df.loc[neutral_mask, neutral_cols].copy()

        return {
            "LLPs": llps,
            "LLPchildren": llp_children,
            "chargedFinalStates": charged,
            "neutralFinalStates": neutral,
        }

    def create_sample_dataframes(self, llpid: int) -> Dict[str, pd.DataFrame]:
        final_states = self.select_final_states()
        llp_children, originating_llp = self._build_llp_children(llpid)

        llps_all = self.select_llps(llpid).copy()
        if len(llp_children):
            keep_llp_idx = set(llp_children["LLPindex"].tolist())
            llps = llps_all[(llps_all.index.isin(keep_llp_idx)) | (llps_all["status"] == 1)].copy()
        else:
            llps = llps_all[llps_all["status"] == 1].copy()

        children_df_indices = set(llp_children.index.tolist()) if len(llp_children) else set()
        fs_no_llp = final_states[~final_states.index.isin(children_df_indices)]
        fs_no_llp = fs_no_llp[fs_no_llp["PID"] != int(llpid)]

        fs_neutrinos = self.select_neutrinos(fs_no_llp)
        fs_no_llp_wo_nu = fs_no_llp[~fs_no_llp["PID"].isin([12, 14, 16, 18])]

        charged = fs_no_llp_wo_nu[(fs_no_llp_wo_nu["charge"] != 0) & (fs_no_llp_wo_nu["charge"] != None)]
        charged = self.select_prompt(charged)
        charged = charged[charged["pt"] > float(self.pt_min_cfg.get("chargedTrack", 0.0))]

        neutral = fs_no_llp_wo_nu[fs_no_llp_wo_nu["charge"] == 0]
        neutral = self.select_prompt(neutral)

        if not llps.empty:
            met_by_event = self._compute_event_met(fs_no_llp_wo_nu)
            llps["METx"] = llps["eventNumber"].map(met_by_event["METx"]).fillna(0.0).to_numpy()
            llps["METy"] = llps["eventNumber"].map(met_by_event["METy"]).fillna(0.0).to_numpy()
            llps["MET"] = PhysicsUtils.pt(llps["METx"].to_numpy(), llps["METy"].to_numpy())
        else:
            llps["METx"] = []
            llps["METy"] = []
            llps["MET"] = []

        return {
            "finalStates": final_states,
            "LLPs": llps,
            "LLPchildren": llp_children,
            "finalStates_NoLLP": fs_no_llp_wo_nu, 
            "finalStates_Neutrinos": fs_neutrinos,
            "chargedFinalStates": charged,
            "neutralFinalStates": neutral,
        }
