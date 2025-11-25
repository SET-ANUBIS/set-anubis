from typing import Optional, Tuple, Any, List

from SetAnubis.core.Selection.domain.Models import HepmcSelectionQuery, IndexWriterConfig, HepmcRef
from SetAnubis.core.Selection.adapters.output.EventsDbHepMCSelector import EventsDbHepmcSelectorAdapter
from SetAnubis.core.Selection.adapters.output.PandasHepMCIndexWriter import PandasHepmcIndexWriterAdapter

def build_index_from_selection(
    *,
    db_path: str,
    storage_dir: str,
    model: Optional[str] = None,
    sql_where: str = "",
    sql_params: Tuple[Any, ...] = tuple(),
    predicate = None,  # callable optionnel: HepmcRef -> bool
    limit: Optional[int] = None,

    index_csv_path: str,
    extra_columns: Optional[dict] = None,  # ex: {"llp_id": 9900012, "geometry": "ceiling"}
    rewrite_in_one_go: bool = True,
    batch_size_rows: int = 50_000,
) -> Tuple[int, int]:
    """
    Select hepmc from db (model+filtres) and write/update csv index with useful columns.
    
    Returns (added_rows, total_rows_after)
    """
    selector = EventsDbHepmcSelectorAdapter(db_path=db_path, storage_dir=storage_dir)
    items: List[HepmcRef] = selector.select(
        HepmcSelectionQuery(
            model=model,
            sql_where=sql_where,
            sql_params=sql_params,
            predicate=predicate,
            limit=limit,
        )
    )
    print("----------------------")
    print(items)
    print("----------------------")
    writer = PandasHepmcIndexWriterAdapter()
    res = writer.write_index(
        items,
        IndexWriterConfig(
            index_csv_path=index_csv_path,
            rewrite_in_one_go=rewrite_in_one_go,
            batch_size_rows=batch_size_rows,
            extra_columns=extra_columns or {},
            dedupe_on_event_id=True,
        )
    )
    print("...........................................")
    print(res.selected_df)
    res.selected_df.to_csv("test.csv")
    print("...........................................")
    
    return res.added_rows, res.total_rows_after

added, total = build_index_from_selection(
    db_path="db/EventsDatabase.db",
    storage_dir="db/EventsStorage",
    model="SM_HeavyN_CKM_AllMasses_LO",
    index_csv_path="outputs/samples_to_process_SM.csv",
    extra_columns={"llp_id": 9900012, "geometry": "ceiling"},
)

print("added : ", added)
print("total : ", total)

added, total = build_index_from_selection(
    db_path="db/EventsDatabase.db",
    storage_dir="db/EventsStorage",
    model=None,
    sql_where="is_decayed=1 AND cross_section > ?",
    sql_params=(1e-6,),
    index_csv_path="outputs/only_decayed.csv",
)

print("added : ", added)
print("total : ", total)

def pred(it: HepmcRef) -> bool:
    m = (it.scan_params or {}).get("mass#9900012")
    try:
        return 1.0 <= float(m) <= 10.0
    except Exception:
        return False

added, total = build_index_from_selection(
    db_path="db/EventsDatabase.db",
    storage_dir="db/EventsStorage",
    predicate=pred,
    index_csv_path="outputs/mass_window.csv",
)

print("added : ", added)
print("total : ", total)