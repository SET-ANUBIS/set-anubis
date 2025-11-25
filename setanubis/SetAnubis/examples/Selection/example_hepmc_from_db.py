from SetAnubis.core.Selection.domain.Models import HepmcSelectionQuery, IndexWriterConfig, HepmcRef
from SetAnubis.core.Selection.adapters.output.EventsDbHepMCSelector import EventsDbHepmcSelectorAdapter
from SetAnubis.core.Selection.adapters.output.PandasHepMCIndexWriter import PandasHepmcIndexWriterAdapter
from typing import Optional, Tuple, Any, List

if __name__ == "__main__":
    
    db_path="db/EventsDatabase.db"
    storage_dir="db/EventsStorage"
    model="SM_HeavyN_CKM_AllMasses_LO"
    index_csv_path="outputs/samples_to_process_SM.csv"
    extra_columns={"llp_id": 9900012, "geometry": "ceiling"}
    sql_where: str = ""
    sql_params: Tuple[Any, ...] = tuple()
    predicate = None
    limit: Optional[int] = None
    rewrite_in_one_go: bool = True
    batch_size_rows: int = 50_000
    
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
    # res.selected_df.to_csv("test.csv")
    print("...........................................")
    
    print(res.added_rows, res.total_rows_after)