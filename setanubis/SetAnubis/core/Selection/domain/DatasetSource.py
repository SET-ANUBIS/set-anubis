from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Protocol, Any
import os, gzip, pickle, hashlib, io
import pandas as pd

from SetAnubis.core.Selection.domain.LLPAnalyzer import LLPAnalyzer

class BundleIO:
    """
    Save and load bundles (dict[str->DataFrame] and full df) implementation with gzip+pickle.
    """
    @staticmethod
    def save_bundle(bundle: Dict[str, pd.DataFrame], filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with gzip.open(filepath, "wb") as f:
            pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load_bundle(filepath: str) -> Dict[str, pd.DataFrame]:
        with gzip.open(filepath, "rb") as f:
            return pickle.load(f)

    @staticmethod
    def save_df(df: pd.DataFrame, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with gzip.open(filepath, "wb") as f:
            pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load_df(filepath: str) -> pd.DataFrame:
        with gzip.open(filepath, "rb") as f:
            return pickle.load(f)


def _sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()[:16]

def _fingerprint_paths(paths: List[str]) -> str:
    """
    for cache (figerprint noms + tailles + mtimes)
    """
    h = hashlib.sha1()
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
    """
    Fingerprint for df (light) : shape + columns + hash of buff csv. Can be change to parquet+hash
    """
    buf = io.BytesIO()

    df.head(min(len(df), 5000)).to_csv(buf, index=False)
    meta = f"{df.shape}-{tuple(df.columns)}".encode()
    return _sha1_bytes(meta + buf.getvalue())


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
    """
    Unique Facade to get bundle(dict[str->DataFrame]) from cache dict, dataframe or hepmc. Deal with df and bundle cache.
    """
    # One of the three needs to exist
    ready_bundle: Optional[Dict[str, pd.DataFrame]] = None
    events_df: Optional[pd.DataFrame] = None
    hepmc_paths: Optional[List[str]] = None
    hepmc_loader: Optional[HepmcLoader] = None

    cfg: SourceConfig = field(default_factory=SourceConfig)

    cache_dir: Optional[str] = None
    df_cache_key: Optional[str] = None 
    force_recompute: bool = False

    def _paths(self, prefix: str) -> Tuple[Optional[str], Optional[str]]:
        if not self.cache_dir:
            return None, None
        os.makedirs(self.cache_dir, exist_ok=True)
        return (os.path.join(self.cache_dir, f"{prefix}_df.pkl.gz"),
                os.path.join(self.cache_dir, f"{prefix}_bundle.pkl.gz"))

    def materialize(self) -> Dict[str, pd.DataFrame]:
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

        analyzer = LLPAnalyzer(df, pt_min_cfg=self.cfg.pt_min_cfg)
        bundle = analyzer.create_sample_dataframes(llpid=self.cfg.llp_pid)

        if self.cache_dir and bundle_path:
            BundleIO.save_bundle(bundle, bundle_path)

        return bundle

    @classmethod
    def from_bundle_dict(cls, bundle: Dict[str, pd.DataFrame]) -> "EventsBundleSource":
        return cls(ready_bundle=bundle)

    @classmethod
    def from_bundle_file(cls, filepath: str) -> "EventsBundleSource":
        bundle = BundleIO.load_bundle(filepath)
        return cls(ready_bundle=bundle)

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
