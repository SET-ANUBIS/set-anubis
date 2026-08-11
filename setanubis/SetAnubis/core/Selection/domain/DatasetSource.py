from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Protocol
import gzip
import hashlib
import io
import os
import pickle
from pathlib import Path
from os import PathLike
import pandas as pd

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

        elif self.hepmc_paths and self.hepmc_loader:
            pkey = _fingerprint_paths(self.hepmc_paths)
            df_path, bundle_path = self._paths(f"hepmc-{pkey}")

            if (not self.force_recompute) and df_path and os.path.exists(df_path):
                df = BundleIO.load_df(df_path)
            else:
                df = self.hepmc_loader(self.hepmc_paths)
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
