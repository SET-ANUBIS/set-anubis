from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Protocol
from itertools import islice
import gzip
import hashlib
import io
import os
import pickle
from pathlib import Path
from os import PathLike
import pandas as pd
import numpy as np

from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer

class BundleIO:
    """Persist trusted pandas bundles using gzip-compressed pickle files.

    Loading is based on the file signature rather than the extension.  This keeps
    older ``.pkl`` files readable when they were written through ``gzip.open``.
    Pickle files can execute code while loading and must therefore come from a
    trusted source.
    """

    GZIP_MAGIC = b"\x1f\x8b"

    @staticmethod
    def _is_gzip(filepath: str | PathLike[str]) -> bool:
        """Return whether *filepath* starts with the gzip magic bytes."""
        with open(filepath, "rb") as stream:
            return stream.read(2) == BundleIO.GZIP_MAGIC

    @staticmethod
    def _dump(value: Any, filepath: str | PathLike[str]) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wb") as stream:
            pickle.dump(value, stream, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _load(filepath: str | PathLike[str]) -> Any:
        opener = gzip.open if BundleIO._is_gzip(filepath) else open
        with opener(filepath, "rb") as stream:
            return pickle.load(stream)

    @staticmethod
    def save_bundle(
        bundle: Dict[str, pd.DataFrame], filepath: str | PathLike[str]
    ) -> None:
        """Write a dataframe bundle as a gzip-compressed trusted pickle."""
        BundleIO._dump(bundle, filepath)

    @staticmethod
    def load_bundle(filepath: str | PathLike[str]) -> Dict[str, pd.DataFrame]:
        """Load a trusted bundle from gzip-compressed or plain pickle data."""
        return BundleIO._load(filepath)

    @staticmethod
    def save_df(df: pd.DataFrame, filepath: str | PathLike[str]) -> None:
        """Write one dataframe as a gzip-compressed trusted pickle."""
        BundleIO._dump(df, filepath)

    @staticmethod
    def load_df(filepath: str | PathLike[str]) -> pd.DataFrame:
        """Load one trusted dataframe from gzip-compressed or plain pickle data."""
        return BundleIO._load(filepath)


def _sha256_bytes(data: bytes) -> str:
    """Return a compact SHA-256 fingerprint for cache identity."""
    return hashlib.sha256(data).hexdigest()[:16]

def _fingerprint_paths(paths: List[str]) -> str:
    """Fingerprint file names, sizes, and modification times for caching."""
    h = hashlib.sha256()
    for p in sorted(map(str, paths)):
        try:
            st = os.stat(p)
            h.update(p.encode())
            h.update(str(st.st_size).encode())
            h.update(str(int(st.st_mtime)).encode())
        except FileNotFoundError:
            h.update(p.encode())
    return h.hexdigest()[:16]

def _fingerprint_df(df: pd.DataFrame) -> str:
    """Build a lightweight dataframe fingerprint from metadata and CSV bytes."""
    buf = io.BytesIO()

    df.head(min(len(df), 5000)).to_csv(buf, index=False)
    meta = f"{df.shape}-{tuple(df.columns)}".encode()
    return _sha256_bytes(meta + buf.getvalue())


class HepmcLoader(Protocol):
    """Abstraction: multiples HepMC -> DataFrame events."""
    def __call__(self, hepmc_paths: List[str]) -> pd.DataFrame: ...


@dataclass(frozen=True)
class SourceConfig:
    llp_pid: int = 9900012 #Default HNL, need to change maybe
    pt_min_cfg: Dict[str, float] = field(default_factory=lambda: {
        "chargedTrack": 5.0, "neutralTrack": 5.0, "jet": 15.0
    })


@dataclass
class EventsBundleSource:
    """Materialize one selection bundle and keep lightweight source provenance.

    A source may come from an already prepared bundle, a dataframe, HepMC, or
    the event database through :meth:`from_event_database`.  ``metadata`` is
    deliberately lightweight and is propagated to the optional selection-results
    database; it never contains the dataframe bundle itself.
    """
    # One of the three needs to exist
    ready_bundle: Optional[Dict[str, pd.DataFrame]] = None
    events_df: Optional[pd.DataFrame] = None
    hepmc_paths: Optional[List[str]] = None
    hepmc_loader: Optional[HepmcLoader] = None

    # Optional native HepMC path.  When provided, SelectionPipeline can build a
    # selection-ready bundle in bounded event chunks instead of first flattening
    # the complete HepMC sample into one very large dataframe.
    native_hepmc_neo_manager: Optional[Any] = None
    native_hepmc_frame_options: Optional[Dict[str, Any]] = None
    hepmc_chunk_size: Optional[int] = None
    hepmc_max_events: Optional[int] = None

    cfg: SourceConfig = field(default_factory=SourceConfig)
    dataset_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    cache_dir: Optional[str] = None
    df_cache_key: Optional[str] = None 
    force_recompute: bool = False

    def _paths(self, prefix: str) -> Tuple[Optional[str], Optional[str]]:
        if not self.cache_dir:
            return None, None
        os.makedirs(self.cache_dir, exist_ok=True)
        return (os.path.join(self.cache_dir, f"{prefix}_df.pkl.gz"),
                os.path.join(self.cache_dir, f"{prefix}_bundle.pkl.gz"))

    def dataset_id(self) -> str:
        """Return the stable source identifier used for provenance and logs."""
        if self.dataset_key:
            return str(self.dataset_key)
        if self.metadata.get("event_id"):
            return str(self.metadata["event_id"])
        if self.hepmc_paths:
            return f"hepmc:{_fingerprint_paths(self.hepmc_paths)}"
        if self.events_df is not None:
            return f"df:{self.df_cache_key or _fingerprint_df(self.events_df)}"
        return "bundle:in-memory"


    def _load_native_hepmc_full(self) -> pd.DataFrame:
        """Historical one-shot fallback for native HepMC sources.

        Chunked preprocessing is preferred for large selections.  This fallback
        keeps native sources usable when the pipeline has transforms/reweighting
        that intentionally require the complete flat dataframe.
        """
        if not self.hepmc_paths or self.native_hepmc_neo_manager is None:
            raise ValueError("Native HepMC source is not configured")

        import pyhepmc
        from SetAnubis.core.Selection.domain.HepMCFrameBuilder import (
            HepmcFrameBuilder,
            HepmcFrameOptions,
        )

        options_dict = dict(self.native_hepmc_frame_options or {})
        if self.hepmc_max_events is not None:
            options_dict["stop_after_events"] = int(self.hepmc_max_events)
        builder = HepmcFrameBuilder(
            neo_manager=self.native_hepmc_neo_manager,
            options=HepmcFrameOptions(**options_dict),
        )

        frames: List[pd.DataFrame] = []
        event_offset = 0
        row_offset = 0
        remaining = self.hepmc_max_events
        for path in self.hepmc_paths:
            if remaining is not None and int(remaining) <= 0:
                break
            local_options = dict(options_dict)
            if remaining is not None:
                local_options["stop_after_events"] = int(remaining)
            local_builder = HepmcFrameBuilder(
                neo_manager=self.native_hepmc_neo_manager,
                options=HepmcFrameOptions(**local_options),
            )
            with pyhepmc.open(path) as stream:
                df, _unknown = local_builder.build_from_events(
                    stream,
                    event_number_start=event_offset,
                    row_index_start=row_offset,
                )
            frames.append(df)
            if not df.empty:
                n_events = int(df["eventNumber"].nunique())
            else:
                n_events = 0
            event_offset += n_events
            row_offset += len(df)
            if remaining is not None:
                remaining = int(remaining) - n_events

        if not frames:
            return pd.DataFrame()
        if len(frames) == 1:
            return frames[0]
        return pd.concat(frames, axis=0, sort=False)

    def materialize(
        self,
        pre_df_transforms: Optional[List[Callable[[pd.DataFrame], pd.DataFrame]]] = None,
        bundle_cache_tag: str = "",
    ) -> Dict[str, pd.DataFrame]:
        if self.ready_bundle is not None:
            return self.ready_bundle

        if self.events_df is not None:
            df = self.events_df
            df_key = self.df_cache_key or _fingerprint_df(df)
            df_path, bundle_path = self._paths(f"df-{df_key}")

        elif self.hepmc_paths and (self.hepmc_loader or self.native_hepmc_neo_manager is not None):
            pkey = _fingerprint_paths(self.hepmc_paths)
            df_path, bundle_path = self._paths(f"hepmc-{pkey}")

            if (not self.force_recompute) and df_path and os.path.exists(df_path):
                df = BundleIO.load_df(df_path)
            else:
                if self.hepmc_loader is not None:
                    df = self.hepmc_loader(self.hepmc_paths)
                else:
                    df = self._load_native_hepmc_full()
                if df_path:
                    BundleIO.save_df(df, df_path)
        else:
            raise ValueError("Provide either ready_bundle, events_df, or (hepmc_paths + hepmc_loader).")

        if self.cache_dir:
            if self.events_df is not None:
                bkey = self.df_cache_key or _fingerprint_df(self.events_df)
                _, bundle_path = self._paths(f"bundle-{bkey}")
            if (not self.force_recompute) and bundle_path and os.path.exists(bundle_path):
                return BundleIO.load_bundle(bundle_path)

        for transform in pre_df_transforms or []:
            df = transform(df)
        
        analyzer = LLPAnalyzer(df, pt_min_cfg=self.cfg.pt_min_cfg)
        bundle = analyzer.create_sample_dataframes(llpid=self.cfg.llp_pid)

        if self.cache_dir and bundle_path:
            BundleIO.save_bundle(bundle, bundle_path)

        return bundle


    def can_materialize_selection_ready_chunked(self) -> bool:
        return bool(
            self.hepmc_paths
            and self.native_hepmc_neo_manager is not None
            and self.hepmc_chunk_size is not None
            and int(self.hepmc_chunk_size) > 0
        )

    def materialize_selection_ready_chunked(self, selection: Any) -> Dict[str, pd.DataFrame]:
        """Build a compact selection-ready bundle from HepMC in bounded chunks.

        Every chunk contains complete events.  Event numbers and dataframe row
        indices receive global offsets, so concatenating the compact LLP frames
        reproduces the same identifiers/order as a one-shot HepMC dataframe.

        Jets and isolation are event-local and are computed before the chunk's
        large flat dataframe and final-state intermediates are released.  Only
        LLPs (with precomputed minDeltaR columns) and LLPchildren survive.
        """
        if not self.can_materialize_selection_ready_chunked():
            raise ValueError("Native chunked HepMC materialization is not configured")

        import pyhepmc
        from SetAnubis.core.Selection.domain.HepMCFrameBuilder import (
            HepmcFrameBuilder,
            HepmcFrameOptions,
        )
        from SetAnubis.core.Selection.domain.JetBuilder import createJetDF
        from SetAnubis.core.Selection.domain.isolation import IsolationComputer

        options_dict = dict(self.native_hepmc_frame_options or {})
        # The outer loop owns event limiting.  A per-chunk stop_after_events
        # would otherwise restart the limit for every chunk.
        options_dict["stop_after_events"] = None
        builder = HepmcFrameBuilder(
            neo_manager=self.native_hepmc_neo_manager,
            options=HepmcFrameOptions(**options_dict),
        )

        chunk_size = int(self.hepmc_chunk_size)
        max_events = (
            None if self.hepmc_max_events is None else int(self.hepmc_max_events)
        )

        llp_parts: List[pd.DataFrame] = []
        child_parts: List[pd.DataFrame] = []
        event_offset = 0
        row_offset = 0
        total_events = 0

        for path in self.hepmc_paths or []:
            with pyhepmc.open(path) as stream:
                while max_events is None or total_events < max_events:
                    take = chunk_size
                    if max_events is not None:
                        take = min(take, max_events - total_events)
                    if take <= 0:
                        break

                    # Keeping only one bounded list of pyhepmc events prevents
                    # the full showered sample from being resident at once.
                    events_chunk = list(islice(stream, take))
                    if not events_chunk:
                        break

                    n_events_chunk = len(events_chunk)
                    df, _unknown = builder.build_from_events(
                        events_chunk,
                        event_number_start=event_offset,
                        row_index_start=row_offset,
                    )
                    # The pyhepmc object graph is no longer needed once the
                    # flat chunk dataframe has been built.
                    del events_chunk

                    event_offset += n_events_chunk
                    total_events += n_events_chunk
                    row_offset += len(df)

                    analyzer = LLPAnalyzer(df, pt_min_cfg=self.cfg.pt_min_cfg)
                    working = analyzer.create_selection_working_set(
                        llpid=self.cfg.llp_pid
                    )
                    # All frames in the working set are independent copies or
                    # projections.  Release the full-width HepMC dataframe and
                    # EventGraph before jet clustering/isolation.
                    del analyzer, df

                    cfs = working.get("chargedFinalStates", pd.DataFrame())
                    nfs = working.get("neutralFinalStates", pd.DataFrame())
                    if not cfs.empty or not nfs.empty:
                        event_arrays = []
                        if not cfs.empty:
                            event_arrays.append(
                                cfs["eventNumber"].to_numpy(dtype=int, copy=False)
                            )
                        if not nfs.empty:
                            event_arrays.append(
                                nfs["eventNumber"].to_numpy(dtype=int, copy=False)
                            )
                        event_numbers = np.unique(np.concatenate(event_arrays))
                        working["finalStatePromptJets"] = createJetDF(
                            event_numbers, cfs, nfs
                        )
                    else:
                        working["finalStatePromptJets"] = pd.DataFrame()

                    llps = working.get("LLPs", pd.DataFrame())
                    if not llps.empty:
                        iso = IsolationComputer(selection=selection)
                        working["LLPs"] = iso.attach_min_delta_r(working)

                    # Append only the two frames SelectionEngine needs.  The
                    # large flat df, charged/neutral states and jets become
                    # unreachable at the end of this loop iteration.
                    llp_parts.append(working.get("LLPs", pd.DataFrame()))
                    child_parts.append(working.get("LLPchildren", pd.DataFrame()))

                    # Do not let loop-local references keep preprocessing frames
                    # alive while the next HepMC chunk is being built.
                    del cfs, nfs, llps, working
                    if "event_arrays" in locals():
                        del event_arrays
                    if "event_numbers" in locals():
                        del event_numbers

        def _concat(parts: List[pd.DataFrame]) -> pd.DataFrame:
            if not parts:
                return pd.DataFrame()
            nonempty = [frame for frame in parts if not frame.empty]
            if not nonempty:
                return parts[0]
            if len(nonempty) == 1:
                return nonempty[0]
            return pd.concat(nonempty, axis=0, sort=False)

        return {
            "LLPs": _concat(llp_parts),
            "LLPchildren": _concat(child_parts),
        }

    @classmethod
    def from_bundle_dict(
        cls,
        bundle: Dict[str, pd.DataFrame],
        *,
        metadata: Optional[Dict[str, Any]] = None,
        dataset_id: Optional[str] = None,
    ) -> "EventsBundleSource":
        """Create a source from an in-memory bundle and optional provenance."""
        return cls(ready_bundle=bundle, metadata=dict(metadata or {}), dataset_key=dataset_id)

    @classmethod
    def from_bundle_file(
        cls,
        filepath: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        dataset_id: Optional[str] = None,
    ) -> "EventsBundleSource":
        """Create a source from a trusted bundle file and optional provenance."""
        bundle = BundleIO.load_bundle(filepath)
        return cls(ready_bundle=bundle, metadata=dict(metadata or {}), dataset_key=dataset_id)

    @classmethod
    def from_event_database(
        cls,
        accessor: Any,
        event_id: str,
        *,
        require_selection_ready: bool = True,
    ) -> "EventsBundleSource":
        """Load one compact bundle and its metadata from an event DB accessor.

        ``accessor`` is intentionally duck-typed to keep the Selection domain
        independent from a concrete database implementation.  The standard
        :class:`EventAccessor` provides ``get_selection_ready_bundle`` and
        ``selection_metadata``.
        """
        bundle = accessor.get_selection_ready_bundle(
            event_id, require_ready=require_selection_ready
        )
        metadata = accessor.selection_metadata(event_id)
        llp_pid = metadata.get("llp_pid")
        cfg = SourceConfig(llp_pid=int(llp_pid)) if llp_pid is not None else SourceConfig()
        return cls(
            ready_bundle=bundle,
            cfg=cfg,
            dataset_key=str(event_id),
            metadata=dict(metadata),
        )

    @classmethod
    def from_events_dataframe(
        cls,
        df: pd.DataFrame,
        cfg: Optional[SourceConfig] = None,
        cache_dir: Optional[str] = None,
        df_cache_key: Optional[str] = None,
        force_recompute: bool = False,
    ) -> "EventsBundleSource":
        return cls(
            events_df=df,
            cfg=cfg or SourceConfig(),
            cache_dir=cache_dir,
            df_cache_key=df_cache_key,
            force_recompute=force_recompute,
        )


    @classmethod
    def from_hepmc_native(
        cls,
        hepmc_paths: List[str],
        *,
        neo_manager: Any,
        cfg: Optional[SourceConfig] = None,
        frame_options: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500,
        max_events: Optional[int] = None,
        cache_dir: Optional[str] = None,
        force_recompute: bool = False,
    ) -> "EventsBundleSource":
        """Create a native chunk-capable HepMC source.

        This is the recommended direct-HepMC input for large samples.  The
        existing ``from_hepmc(..., hepmc_loader=...)`` API remains unchanged.
        """
        return cls(
            hepmc_paths=list(hepmc_paths),
            native_hepmc_neo_manager=neo_manager,
            native_hepmc_frame_options=dict(frame_options or {}),
            hepmc_chunk_size=int(chunk_size),
            hepmc_max_events=max_events,
            cfg=cfg or SourceConfig(),
            cache_dir=cache_dir,
            force_recompute=force_recompute,
        )

    @classmethod
    def from_hepmc(
        cls,
        hepmc_paths: List[str],
        hepmc_loader: HepmcLoader,
        cfg: Optional[SourceConfig] = None,
        cache_dir: Optional[str] = None,
        force_recompute: bool = False,
    ) -> "EventsBundleSource":
        return cls(
            hepmc_paths=hepmc_paths,
            hepmc_loader=hepmc_loader,
            cfg=cfg or SourceConfig(),
            cache_dir=cache_dir,
            force_recompute=force_recompute,
        )
