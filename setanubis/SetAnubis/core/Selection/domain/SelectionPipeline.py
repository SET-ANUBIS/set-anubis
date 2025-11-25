from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol, Any, Iterable

import numpy as np
import pandas as pd
import os
import pickle
import gzip

from SetAnubis.core.Selection.domain.SelectionEngine import (
    SelectionEngine, SelectionConfig, RunConfig
)
import dataclasses
from SetAnubis.core.Selection.domain.JetBuilder import createJetDF
from SetAnubis.core.Selection.domain.isolation import IsolationComputer
from SetAnubis.core.Selection.domain.ReweightTransformer import (
    DataBundle, ReweightDecayPositions, RandomProvider
)

from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource, BundleIO, SourceConfig

class IDataSource(Protocol):
    """Return a df or and bundle already prepared."""
    def load_df(self) -> pd.DataFrame: ...
    def dataset_id(self) -> str: ... 
    
class ICache(Protocol):
    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any) -> None: ...


class InMemoryCache(ICache):
    def __init__(self) -> None:
        self._m: Dict[str, Any] = {}
    def get(self, key: str) -> Optional[Any]:
        return self._m.get(key)
    def set(self, key: str, value: Any) -> None:
        self._m[key] = value


class FileCache(ICache):
    def __init__(self, root_dir: str) -> None:
        self.root = root_dir
        os.makedirs(self.root, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.root, f"{key}.pkl.gz")

    def get(self, key: str) -> Optional[Any]:
        p = self._path(key)
        if not os.path.isfile(p):
            return None
        with gzip.open(p, "rb") as f:
            return pickle.load(f)

    def set(self, key: str, value: Any) -> None:
        p = self._path(key)
        tmp = f"{p}.tmp"
        with gzip.open(tmp, "wb") as f:
            pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, p)


class PreDFTransform(Protocol):
    """Transform a event df before the bundle construction."""
    def __call__(self, df: pd.DataFrame) -> pd.DataFrame: ...

class PostBundleTransform(Protocol):
    """Transform the bundle dict[str->DataFrame] after createSampleDataFrames()."""
    def __call__(self, bundle: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]: ...

@dataclass(frozen=True)
class PipelineOptions:
    """
    Option for the pipeline construction.
    """
    add_jets: bool = True
    compute_isolation: bool = True
    selection_mode: str = "standard"   # "standard" | "2dv"
    # Reweight: If True, we onl apply transfo if a reweighter is done.
    enable_reweight_gate: bool = True

@dataclass
class SelectionPipeline:
    """
    Executable pipeline. Need a source, geometry and configuration to run.
    """
    engine: SelectionEngine
    options: PipelineOptions
    pre_df_transforms: List[PreDFTransform]
    post_bundle_transforms: List[PostBundleTransform]
    reweighter: Optional[ReweightDecayPositions] = None

    def _maybe_reweight(self, bundle: Dict[str, pd.DataFrame], run_cfg: RunConfig) -> Dict[str, pd.DataFrame]:
        if not self.reweighter:
            return bundle
        if self.options.enable_reweight_gate and not run_cfg.reweightLifetime:
            return bundle

        try:
            from SetAnubis.core.Selection.domain.ReweightTransformer import DataBundle
        except Exception:
            return bundle

        allowed = {f.name for f in dataclasses.fields(DataBundle)}

        # Sépare core/extras (extras = added tables like finalStatePromptJets)
        core_dict   = {k: v for k, v in bundle.items() if k in allowed}
        extras_dict = {k: v for k, v in bundle.items() if k not in allowed}

        # Apply transformation on core
        db  = DataBundle.from_dict(core_dict)
        db2 = self.reweighter.apply(db)
        out = db2.to_dict()

        # Extra (unchanged) reinjection.
        for k, v in extras_dict.items():
            out[k] = v

        return out

    def _ensure_jets_and_isolation(self, bundle: Dict[str, pd.DataFrame], sel_cfg: SelectionConfig) -> Dict[str, pd.DataFrame]:
        out = dict(bundle)
        LLPs = out.get("LLPs", pd.DataFrame())
        cfs  = out.get("chargedFinalStates", pd.DataFrame())
        nfs  = out.get("neutralFinalStates", pd.DataFrame())

        if self.options.add_jets:
            if not cfs.empty or not nfs.empty:
                ev = np.unique(np.concatenate([
                    cfs["eventNumber"].to_numpy(dtype=int, copy=False) if not cfs.empty else np.array([], dtype=int),
                    nfs["eventNumber"].to_numpy(dtype=int, copy=False) if not nfs.empty else np.array([], dtype=int),
                ]))
                out["finalStatePromptJets"] = createJetDF(ev, cfs, nfs)

        if self.options.compute_isolation and not LLPs.empty:
            iso = IsolationComputer(selection=sel_cfg)
            out["LLPs"] = iso.attach_min_delta_r(out)

        return out

    def run(self, source: EventsBundleSource, sel_cfg: SelectionConfig, run_cfg: RunConfig) -> Dict[str, Any]:
        # Bundle  (already cached by source)
        bundle = source.materialize()

        # Post-bundle transforms
        for t in self.post_bundle_transforms:
            bundle = t(bundle)

        # REWEIGHT first (bundle is still core here.)
        bundle = self._maybe_reweight(bundle, run_cfg)

        # Jets/Isolation (add finalStatePromptJets, minDeltaR, etc.)
        bundle = self._ensure_jets_and_isolation(bundle, sel_cfg)

        # Selection
        if self.options.selection_mode.lower() in ("2dv", "two-dv", "twodv"):
            result = self.engine.apply_2dv_selection(bundle, run_cfg, sel_cfg)
        else:
            result = self.engine.apply_selection(bundle, run_cfg, sel_cfg)

        return result


@dataclass
class SelectionPipelineBuilder:
    """
    Build a pipeline step by step. No dependance with source (df, hepmc or bundle).
    """
    engine: SelectionEngine = field(default_factory=SelectionEngine)
    options: PipelineOptions = field(default_factory=PipelineOptions)

    _pre_df_transforms: List[PreDFTransform] = field(default_factory=list)
    _post_bundle_transforms: List[PostBundleTransform] = field(default_factory=list)
    _reweighter: Optional[ReweightDecayPositions] = None

    def set_options(self, **kwargs) -> "SelectionPipelineBuilder":
        self.options = PipelineOptions(**{**self.options.__dict__, **kwargs})
        return self

    def add_pre_df_transform(self, transform: PreDFTransform) -> "SelectionPipelineBuilder":
        self._pre_df_transforms.append(transform)
        return self

    def add_post_bundle_transform(self, transform: PostBundleTransform) -> "SelectionPipelineBuilder":
        self._post_bundle_transforms.append(transform)
        return self

    def set_reweighter(self, lifetime_s: Optional[float], llp_pid: Optional[int], seed: int = 42) -> "SelectionPipelineBuilder":
        """
        Install a reweighted by default (if lifetime/pid given). If not, no reweight.
        """
        if lifetime_s is not None and llp_pid is not None:
            self._reweighter = ReweightDecayPositions(
                lifetime_s=float(lifetime_s),
                llp_pid=int(llp_pid),
                rng=RandomProvider(seed=seed),
            )
        else:
            self._reweighter = None
        return self

    def build(self) -> SelectionPipeline:
        return SelectionPipeline(
            engine=self.engine,
            options=self.options,
            pre_df_transforms=self._pre_df_transforms[:],
            post_bundle_transforms=self._post_bundle_transforms[:],
            reweighter=self._reweighter,
        )
