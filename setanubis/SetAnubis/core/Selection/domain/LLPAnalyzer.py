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
            raise ValueError(f"Colonnes manquantes dans df: {missing}")


class EventGraph:
    """
    Graph representation by event:
     O(1) access to children of an event/particleIndex 
     O(1) access if a PID and nChildren of an event/particleIndex 
     O(1) of the pandas line index from event/particleIndex
    """
    def __init__(self, df: pd.DataFrame) -> None:
        Schema.ensure(df)
        self.df = df

        self._row_index: Dict[Tuple[int, int], int] = {
            (int(ev), int(pidx)): int(i)
            for i, ev, pidx in zip(df.index, df["eventNumber"].to_list(), df["particleIndex"].to_list())
        }

        def _to_list(x) -> List[int]:
            if isinstance(x, list):
                return x
            if isinstance(x, str):
                try:
                    v = ast.literal_eval(x)
                    return v if isinstance(v, list) else []
                except Exception:
                    return []
            return []

        children_series = df["childrenIndices"].apply(_to_list)

        # (event, pidx) -> [child_pidx, etc.]
        self._children: Dict[Tuple[int, int], List[int]] = {
            (int(ev), int(pidx)): list(children)
            for ev, pidx, children in zip(df["eventNumber"].to_list(),
                                          df["particleIndex"].to_list(),
                                          children_series.to_list())
        }

        # (event, pidx) -> PID, nChildren
        self._pid: Dict[Tuple[int, int], int] = {
            (int(ev), int(pidx)): int(pid)
            for ev, pidx, pid in zip(df["eventNumber"].to_list(),
                                     df["particleIndex"].to_list(),
                                     df["PID"].to_list())
        }
        self._nchildren: Dict[Tuple[int, int], int] = {
            (int(ev), int(pidx)): int(nc) if not pd.isna(nc) else 0
            for ev, pidx, nc in zip(df["eventNumber"].to_list(),
                                    df["particleIndex"].to_list(),
                                    df["nChildren"].to_list())
        }

    #$ O(1) access
    def row_of(self, event: int, pidx: int) -> Optional[int]:
        return self._row_index.get((int(event), int(pidx)))

    def children_of(self, event: int, pidx: int) -> List[int]:
        return self._children.get((int(event), int(pidx)), [])

    def pid_of(self, event: int, pidx: int) -> int:
        return self._pid.get((int(event), int(pidx)), 0)

    def nchildren_of(self, event: int, pidx: int) -> int:
        return self._nchildren.get((int(event), int(pidx)), 0)


# Hunter (itarative DFS without recursion)
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

            skip_child = (
                (child_pid in self.llp_pids) and
                (parent_pid_cur in self.llp_pids) and
                (child_pid == parent_pid_cur) and
                (parent_nc_cur == 1)
            )

            #LLP -> LLP
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
        self.df = df.copy()
        self.pt_min_cfg = dict(pt_min_cfg)
        self.graph = EventGraph(self.df)

    # atomique selection.
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

        charged = fs_no_llp_wo_nu[(fs_no_llp_wo_nu["charge"] != 0) & (fs_no_llp_wo_nu["charge"] != -0.555)]
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
