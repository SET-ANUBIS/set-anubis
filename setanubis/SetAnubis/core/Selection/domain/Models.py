from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Protocol, Callable

@dataclass(frozen=True)
class HepmcRef:
    """run representation."""
    event_id: str
    model: Optional[str]
    run_name: Optional[str]
    hepmc_path: str       
    cross_section_pb: Optional[float] = None
    scan_params: Optional[Dict[str, Any]] = None
    scan_widths: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class HepmcSelectionQuery:
    """Selection parameters, domain only (No I/O)."""
    model: Optional[str] = None
    # SQL Filter
    sql_where: str = ""
    sql_params: Tuple[Any, ...] = tuple()
    # Optional filter on hepmcref
    predicate: Optional[Callable[[HepmcRef], bool]] = None
    limit: Optional[int] = None

@dataclass(frozen=True)
class IndexWriterConfig:
    """Index csv writing config (No I/O)."""
    index_csv_path: str
    batch_size_rows: int = 50_000
    rewrite_in_one_go: bool = True   # True = concat + 1 write; False = append by batch
    dedupe_on_event_id: bool = True  # avoid duplicate if indexed
    extra_columns: Optional[Dict[str, Any]] = None  # e.g: {"llp_id": 9900012, "model_tag": "HNL"}

@dataclass(frozen=True)
class IndexWriteResult:
    added_rows: int
    total_rows_after: int
    deduped_rows: int
    selected_df: Any | None = None
