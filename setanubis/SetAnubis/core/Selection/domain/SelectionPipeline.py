from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol, Any, Iterable, Mapping

import numpy as np
import pandas as pd
import os
import pickle
import gzip
from pathlib import Path

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
from SetAnubis.core.Selection.domain.PhiFoldTransform import phi_fold_df

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
    phiFold: bool = False

def _selection_geometry_payload(geometry: Any) -> Dict[str, Any]:
    """Return stable, human-readable geometry metadata for result provenance."""
    payload: Dict[str, Any] = {
        "adapter_class": f"{geometry.__class__.__module__}.{geometry.__class__.__name__}"
    }
    region = getattr(geometry, "default_decay_region", None)
    payload["default_decay_region"] = getattr(region, "value", str(region) if region is not None else None)
    radius = getattr(geometry, "default_fiducial_radius", None)
    if radius is not None:
        try:
            payload["default_fiducial_radius"] = float(radius)
        except Exception:
            payload["default_fiducial_radius"] = repr(radius)

    concrete = getattr(geometry, "_geometry", None)
    if concrete is not None:
        payload["geometry_class"] = f"{concrete.__class__.__module__}.{concrete.__class__.__name__}"
        cfg = getattr(concrete, "_cfg", None)
        if cfg is not None:
            try:
                payload["geometry_config"] = dataclasses.asdict(cfg) if dataclasses.is_dataclass(cfg) else dict(vars(cfg))
            except Exception:
                payload["geometry_config"] = repr(cfg)
    return payload


def _selection_config_payload(sel_cfg: SelectionConfig) -> Dict[str, Any]:
    """Serialize the physics cuts without trying to pickle the geometry object."""
    return {
        "geometry": _selection_geometry_payload(sel_cfg.geometry),
        "minMET": float(sel_cfg.minMET),
        "minP": dataclasses.asdict(sel_cfg.minP),
        "minPt": dataclasses.asdict(sel_cfg.minPt),
        "minDR": dataclasses.asdict(sel_cfg.minDR),
        "nStations": int(sel_cfg.nStations),
        "nIntersections": int(sel_cfg.nIntersections),
        "nTracks": int(sel_cfg.nTracks),
        "eachTrack": bool(sel_cfg.eachTrack),
        "RPCeff": float(sel_cfg.RPCeff),
        "nRPCsPerLayer": int(sel_cfg.nRPCsPerLayer),
    }


def _run_config_payload(run_cfg: RunConfig) -> Dict[str, Any]:
    """Return runtime switches used by one selection execution."""
    return dataclasses.asdict(run_cfg)


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

        core_dict   = {k: v for k, v in bundle.items() if k in allowed}
        extras_dict = {k: v for k, v in bundle.items() if k not in allowed}

        db  = DataBundle.from_dict(core_dict)
        db2 = self.reweighter.apply(db)
        out = db2.to_dict()

        for k, v in extras_dict.items():
            out[k] = v

        return out

    def _ensure_jets_and_isolation(self, bundle: Dict[str, pd.DataFrame], sel_cfg: SelectionConfig) -> Dict[str, pd.DataFrame]:
        out = dict(bundle)
        LLPs = out.get("LLPs", pd.DataFrame())
        cfs  = out.get("chargedFinalStates", pd.DataFrame())
        nfs  = out.get("neutralFinalStates", pd.DataFrame())

        # Database bundles can now be stored after JetBuilder.  In that case we
        # must not rebuild jets from a pruned bundle, because neutralFinalStates
        # is intentionally absent and rebuilding would silently overwrite the
        # correct finalStatePromptJets with charged-only jets.
        have_prebuilt_jets = (
            "finalStatePromptJets" in out
            and isinstance(out.get("finalStatePromptJets"), pd.DataFrame)
        )
        if self.options.add_jets and not have_prebuilt_jets:
            if not cfs.empty or not nfs.empty:
                ev = np.unique(np.concatenate([
                    cfs["eventNumber"].to_numpy(dtype=int, copy=False) if not cfs.empty else np.array([], dtype=int),
                    nfs["eventNumber"].to_numpy(dtype=int, copy=False) if not nfs.empty else np.array([], dtype=int),
                ]))
                out["finalStatePromptJets"] = createJetDF(ev, cfs, nfs)

        # Same idea for isolation: selection-ready DB bundles already have
        # minDeltaR_Jets/minDeltaR_Tracks attached to LLPs.  Do not overwrite
        # them unless the columns are absent.
        have_precomputed_iso = (
            not LLPs.empty
            and "minDeltaR_Jets" in LLPs.columns
            and "minDeltaR_Tracks" in LLPs.columns
        )
        if self.options.compute_isolation and not LLPs.empty and not have_precomputed_iso:
            iso = IsolationComputer(selection=sel_cfg)
            out["LLPs"] = iso.attach_min_delta_r(out)

        return out


    @staticmethod
    def _prune_selection_ready_bundle(bundle: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Drop preprocessing frames once isolation is embedded in LLPs.

        SelectionEngine needs only LLPs and LLPchildren when minDeltaR_Jets and
        minDeltaR_Tracks are already present on LLPs.  Keeping charged/neutral
        final states and jets alive beyond this point only increases peak RSS.
        """
        llps = bundle.get("LLPs", pd.DataFrame())
        have_iso = (
            isinstance(llps, pd.DataFrame)
            and "minDeltaR_Jets" in llps.columns
            and "minDeltaR_Tracks" in llps.columns
        )
        if not have_iso:
            return bundle
        return {
            "LLPs": llps,
            "LLPchildren": bundle.get("LLPchildren", pd.DataFrame()),
        }

    def _pipeline_provenance(self) -> Dict[str, Any]:
        """Return options that affect cut-flow reproducibility."""
        payload: Dict[str, Any] = {"options": dataclasses.asdict(self.options)}
        if self.reweighter is not None:
            payload["reweighter"] = {
                "class": f"{self.reweighter.__class__.__module__}.{self.reweighter.__class__.__name__}",
                "lifetime_s": float(self.reweighter.lifetime_s),
                "llp_pid": int(self.reweighter.llp_pid),
                "kernels": [getattr(kernel, "name", kernel.__class__.__name__) for kernel in self.reweighter.kernels],
            }
        else:
            payload["reweighter"] = None
        payload["pre_df_transforms"] = [getattr(t, "__name__", t.__class__.__name__) for t in self.pre_df_transforms]
        payload["post_bundle_transforms"] = [getattr(t, "__name__", t.__class__.__name__) for t in self.post_bundle_transforms]
        return payload

    @staticmethod
    def _resolve_results_db(results_db: Any) -> Any:
        """Accept either a result DB manager object or a SQLite path."""
        if results_db is None:
            raise ValueError("results_db is required when store=True")
        if isinstance(results_db, (str, os.PathLike, Path)):
            from SetAnubis.core.DataBase.domain.SelectionResultsDatabaseManager import (
                SelectionResultsDatabaseManager,
            )
            return SelectionResultsDatabaseManager(str(results_db))
        if not hasattr(results_db, "store_result"):
            raise TypeError("results_db must be a SelectionResultsDatabaseManager or a database path")
        return results_db

    def run(
        self,
        source: EventsBundleSource,
        sel_cfg: SelectionConfig,
        run_cfg: RunConfig,
        *,
        store: bool = False,
        results_db: Any = None,
        analysis_name: str = "default",
        on_conflict: str = "replace",
        extra_metadata: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        pre_df_transforms = list(self.pre_df_transforms)

        if getattr(self.options, "phiFold", False):
            pre_df_transforms.append(lambda df: phi_fold_df(df, source.cfg.llp_pid))
        
        # Bundle.  For a native large-HepMC source with no transforms/reweighting,
        # preprocess in bounded event chunks and retain only LLPs/LLPchildren.
        # Any feature whose semantics could depend on the full dataframe keeps
        # the historical one-shot path.
        can_chunk = (
            hasattr(source, "can_materialize_selection_ready_chunked")
            and source.can_materialize_selection_ready_chunked()
            and not pre_df_transforms
            and not self.post_bundle_transforms
            and self.reweighter is None
        )
        if can_chunk:
            bundle = source.materialize_selection_ready_chunked(sel_cfg)
        else:
            bundle = source.materialize(
                pre_df_transforms=pre_df_transforms,
                bundle_cache_tag=f"phiFold={getattr(self.options, 'phiFold', False)}",
            )

        # Post-bundle transforms
        for t in self.post_bundle_transforms:
            bundle = t(bundle)

        # REWEIGHT first (bundle is still core here.)
        bundle = self._maybe_reweight(bundle, run_cfg)

        # Jets/Isolation (add finalStatePromptJets, minDeltaR, etc.)
        bundle = self._ensure_jets_and_isolation(bundle, sel_cfg)

        # Once minDeltaR is attached, all jet/track/final-state frames are
        # preprocessing-only.  Do not keep them resident during SelectionEngine.
        bundle = self._prune_selection_ready_bundle(bundle)

        # Selection
        if self.options.selection_mode.lower() in ("2dv", "two-dv", "twodv"):
            result = self.engine.apply_2dv_selection(bundle, run_cfg, sel_cfg)
        else:
            result = self.engine.apply_selection(bundle, run_cfg, sel_cfg)

        if store:
            metadata = dict(getattr(source, "metadata", {}) or {})
            if not metadata.get("event_id"):
                raise ValueError(
                    "Selection result storage requires source provenance with event_id. "
                    "Use EventsBundleSource.from_event_database(...) or provide metadata explicitly."
                )
            db = self._resolve_results_db(results_db)
            stored_result_id = db.store_result(
                event_metadata=metadata,
                cut_flow=result.get("cutFlow", {}),
                selection_config=_selection_config_payload(sel_cfg),
                run_config=_run_config_payload(run_cfg),
                pipeline_options=self._pipeline_provenance(),
                analysis_name=analysis_name,
                on_conflict=on_conflict,
                extra_metadata=extra_metadata,
            )
            result["stored_result_id"] = stored_result_id

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
