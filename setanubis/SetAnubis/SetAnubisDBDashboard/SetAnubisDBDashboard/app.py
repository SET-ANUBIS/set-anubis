import argparse
import os
import traceback
from typing import Any, Dict, List, Optional

from dash import Dash, Input, Output, State, callback_context, dcc, html, no_update
from dash.exceptions import PreventUpdate

from . import data as dbdata
from .components import card, data_table, graph_card, metric, metrics_row, status_box
from .figures import (
    artifact_sizes,
    bundle_frames,
    cross_section_hist,
    events_by_model,
    import_timeline,
    model_storage,
    particle_masses,
    particle_widths,
    per_event_storage,
    scan_scatter,
    storage_breakdown,
    storage_ratio_hist,
)
from .formatting import human_bytes, human_number, human_percent, pretty_json, short_id

DEFAULT_DB = os.environ.get("SETANUBIS_DB_PATH", "db/EventsDatabase.db")
DEFAULT_STORAGE = os.environ.get("SETANUBIS_STORAGE_DIR", "db/EventsStorage")
DEFAULT_EVENTS_ROOT = os.environ.get("SETANUBIS_EVENTS_ROOT", "db/Events_THEO")


def _int_or_none(value: Any) -> Optional[int]:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(str(value).strip())
    except Exception:
        return None


def _bool_from_dropdown(value: str) -> Optional[bool]:
    if value == "yes":
        return True
    if value == "no":
        return False
    return None


def _event_options(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    opts = []
    for e in payload.get("events") or []:
        label = f"{e.get('run_name') or short_id(e.get('id'))} • {e.get('model') or 'no model'}"
        opts.append({"label": label, "value": e.get("id")})
    return opts


def _model_options(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for m in payload.get("models") or []:
        model = m.get("model")
        if model:
            out.append({"label": f"{model} ({m.get('n_events', 0)})", "value": model})
    return out


def _events_for_table(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for e in events:
        rows.append({
            "id": e.get("id"),
            "event": short_id(e.get("id")),
            "run": e.get("run_name"),
            "pre_decay": e.get("pre_decay_run_name"),
            "model": e.get("model"),
            "llp": e.get("llp_pid"),
            "xsec_pb": e.get("cross_section_pb"),
            "seed": e.get("seed"),
            "format": e.get("sample_bundle_format"),
            "hepmc": human_bytes(e.get("source_hepmc_size_bytes")),
            "runs": human_bytes(e.get("original_runs_total_size_bytes")),
            "bundle": human_bytes(e.get("stored_bundle_size_bytes")),
            "bundle/runs": human_percent(e.get("bundle_over_original_runs")),
            "saved": human_bytes(e.get("saved_vs_original_runs_bytes")),
            "hepmc_stored": "yes" if e.get("hepmc_stored") else "no",
        })
    return rows


def _particles_for_table(particles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for p in particles:
        out.append({
            "pdg": p.get("pdg"),
            "name": p.get("name"),
            "model": p.get("model"),
            "mass": p.get("mass"),
            "width": p.get("width"),
            "charge": p.get("charge"),
            "spin": p.get("spin"),
            "color": p.get("color"),
            "occurrences": p.get("occurrences"),
        })
    return out


def _metric_items(payload: Dict[str, Any]):
    storage = payload.get("storage") or {}
    saved_original = storage.get("saved_vs_original_runs_bytes")
    ratio_original = storage.get("bundle_over_original_runs")
    return [
        metric("Events", human_number(storage.get("events")), f"bundles: {human_number(storage.get('events_with_bundles'))}"),
        metric("Models", human_number(storage.get("models")), f"HEPMC stored: {human_number(storage.get('events_with_stored_hepmc'))}"),
        metric("CAS", human_bytes(storage.get("cas_size_bytes")), f"blobs: {human_number(storage.get('cas_blobs'))}"),
        metric("Original runs", human_bytes(storage.get("original_runs_total_size_bytes")), "pre-decay + decayed folders"),
        metric("Stored bundles", human_bytes(storage.get("stored_bundle_size_bytes")), f"bundle/original: {human_percent(ratio_original)}", "good" if ratio_original is not None and ratio_original < 0.5 else "warn"),
        metric("Saved", human_bytes(saved_original), "vs original folders", "good" if saved_original and saved_original > 0 else ""),
    ]


def controls_sidebar(default_db: str, default_storage: str, default_events_root: str, logo_src: str) -> html.Div:
    return html.Div(
        className="grid",
        children=[
            html.Div(className="brand", children=[
                html.Img(src=logo_src, alt="SET-ANUBIS logo", className="brand-logo"),
                html.Div(className="brand-copy", children=[
                    html.H1("SET-ANUBIS DB dashboard"),
                    html.Div("Audit stored runs, bundle sizes and scan metadata.", className="brand-subtitle"),
                ]),
                html.Div("Dash", className="badge"),
            ]),
            card(
                "Database",
                "SQLite + CAS",
                [
                    html.Div("DB path", className="label"),
                    dcc.Input(id="db-path", type="text", value=default_db, style={"width": "100%"}),
                    html.Div("Storage dir", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="storage-dir", type="text", value=default_storage, style={"width": "100%"}),
                    html.Div("Events root for storage refresh", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="events-root", type="text", value=default_events_root, style={"width": "100%"}),
                    html.Hr(),
                    html.Button("Load / Refresh dashboard", id="refresh-btn", n_clicks=0),
                    html.Div(style={"height": "8px"}),
                    html.Button("Backfill storage metadata", id="backfill-btn", n_clicks=0),
                    html.Div(id="status-line", className="status"),
                ],
            ),
            card(
                "Filters",
                "applied on refresh",
                [
                    html.Div("Model", className="label"),
                    dcc.Dropdown(id="model-filter", options=[], value=None, clearable=True, placeholder="All models"),
                    html.Div("LLP PID", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="llp-pid-filter", type="text", value="", placeholder="9900012", style={"width": "100%"}),
                    html.Div("Bundle status", className="label", style={"marginTop": "10px"}),
                    dcc.Dropdown(
                        id="bundle-filter",
                        options=[
                            {"label": "All events", "value": "all"},
                            {"label": "Only events with bundle", "value": "yes"},
                            {"label": "Only events without bundle", "value": "no"},
                        ],
                        value="all",
                        clearable=False,
                    ),
                    html.Div("Event limit", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="event-limit", type="text", value="500", style={"width": "100%"}),
                    html.Hr(),
                    dcc.Checklist(
                        id="include-particles",
                        options=[{"label": "parse particle catalog from stored banners", "value": "yes"}],
                        value=["yes"],
                        className="checklist",
                    ),
                ],
            ),
            card(
                "Particle lookup",
                "from banner metadata",
                [
                    html.Div("PDG", className="label"),
                    dcc.Input(id="particle-pdg", type="text", value="9900012", style={"width": "100%"}),
                    html.Div("Decay channels shown", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="particle-max-channels", type="text", value="25", style={"width": "100%"}),
                    html.Button("Inspect particle", id="particle-btn", n_clicks=0, style={"marginTop": "10px"}),
                ],
            ),
        ],
    )


def overview_page(payload: Dict[str, Any]) -> html.Div:
    return html.Div(
        className="content",
        children=[
            metrics_row(_metric_items(payload)),
            html.Div(
                className="graph-row-2",
                children=[
                    graph_card("Events by model", dcc.Graph(figure=events_by_model(payload.get("models") or []), style={"height": "35vh"}), "imported runs"),
                    graph_card("Import timeline", dcc.Graph(figure=import_timeline(payload.get("events") or []), style={"height": "35vh"}), "date_added"),
                ],
            ),
            html.Div(
                className="graph-row",
                children=[
                    graph_card("Cross-section", dcc.Graph(figure=cross_section_hist(payload.get("events") or []), style={"height": "32vh"}), "pb"),
                    graph_card("Scan overview", dcc.Graph(figure=scan_scatter(payload.get("events") or []), style={"height": "32vh"}), "first numeric scan param"),
                    graph_card("Stored frames", dcc.Graph(figure=bundle_frames(payload.get("bundle_frames") or {}), style={"height": "32vh"}), "rows per frame"),
                ],
            ),
        ],
    )


def storage_page(payload: Dict[str, Any]) -> html.Div:
    return html.Div(
        className="content",
        children=[
            metrics_row([
                metric("Source HEPMC", human_bytes((payload.get("storage") or {}).get("source_hepmc_size_bytes")), "sum over events"),
                metric("Original folders", human_bytes((payload.get("storage") or {}).get("original_runs_total_size_bytes")), "run + run_decayed"),
                metric("Bundles", human_bytes((payload.get("storage") or {}).get("stored_bundle_size_bytes")), "stored dataframe dicts", "good"),
                metric("Bundle / HEPMC", human_percent((payload.get("storage") or {}).get("bundle_over_source_hepmc")), "lower is better"),
                metric("Bundle / folders", human_percent((payload.get("storage") or {}).get("bundle_over_original_runs")), "lower is better"),
            ]),
            html.Div(
                className="graph-row-2",
                children=[
                    graph_card("Global storage", dcc.Graph(figure=storage_breakdown(payload.get("storage") or {}), style={"height": "38vh"}), "bytes, log scale when useful"),
                    graph_card("Artifacts", dcc.Graph(figure=artifact_sizes(payload.get("artifacts") or []), style={"height": "38vh"}), "CAS artifacts"),
                ],
            ),
            html.Div(
                className="graph-row",
                children=[
                    graph_card("Per-event storage", dcc.Graph(figure=per_event_storage(payload.get("events") or []), style={"height": "36vh"}), "original vs bundle"),
                    graph_card("Compression ratio", dcc.Graph(figure=storage_ratio_hist(payload.get("events") or []), style={"height": "36vh"}), "bundle/original"),
                    graph_card("Storage by model", dcc.Graph(figure=model_storage(payload.get("models") or []), style={"height": "36vh"}), "grouped bytes"),
                ],
            ),
        ],
    )


def events_page(payload: Dict[str, Any]) -> html.Div:
    table_rows = _events_for_table(payload.get("events") or [])
    columns = [
        {"name": "event", "id": "event"},
        {"name": "run", "id": "run"},
        {"name": "pre-decay", "id": "pre_decay"},
        {"name": "model", "id": "model"},
        {"name": "llp", "id": "llp"},
        {"name": "xsec [pb]", "id": "xsec_pb"},
        {"name": "seed", "id": "seed"},
        {"name": "format", "id": "format"},
        {"name": "HEPMC", "id": "hepmc"},
        {"name": "runs", "id": "runs"},
        {"name": "bundle", "id": "bundle"},
        {"name": "bundle/runs", "id": "bundle/runs"},
        {"name": "saved", "id": "saved"},
        {"name": "HEPMC stored", "id": "hepmc_stored"},
    ]
    return html.Div(
        className="content",
        children=[
            html.Div(
                className="grid",
                style={"gridTemplateColumns": "1.2fr 0.8fr"},
                children=[
                    card("Events", f"{len(table_rows)} rows", [data_table("events-table", columns, table_rows, page_size=14, row_selectable="single")]),
                    card(
                        "Selected event",
                        "storage + metadata preview",
                        [
                            html.Div("Select one row in the table.", id="selected-event-summary", className="status"),
                            html.Hr(),
                            html.Pre("{}", id="selected-event-json", className="json-pre"),
                        ],
                    ),
                ],
            )
        ],
    )


def particles_page(payload: Dict[str, Any]) -> html.Div:
    rows = _particles_for_table(payload.get("particles") or [])
    cols = [
        {"name": "PDG", "id": "pdg"},
        {"name": "name", "id": "name"},
        {"name": "model", "id": "model"},
        {"name": "mass", "id": "mass"},
        {"name": "width", "id": "width"},
        {"name": "charge", "id": "charge"},
        {"name": "spin", "id": "spin"},
        {"name": "color", "id": "color"},
        {"name": "occ.", "id": "occurrences"},
    ]
    return html.Div(
        className="content",
        children=[
            html.Div(
                className="graph-row-2",
                children=[
                    graph_card("Mass spectrum", dcc.Graph(figure=particle_masses(payload.get("particles") or []), style={"height": "34vh"}), "from SLHA MASS block"),
                    graph_card("Widths", dcc.Graph(figure=particle_widths(payload.get("particles") or []), style={"height": "34vh"}), "from DECAY blocks"),
                ],
            ),
            html.Div(
                className="grid",
                style={"gridTemplateColumns": "1.1fr 0.9fr"},
                children=[
                    card("Particles", f"{len(rows)} particles", [data_table("particles-table", cols, rows, page_size=14)]),
                    card(
                        "Particle detail",
                        "lookup result",
                        [
                            html.Div("Use the PDG input in the sidebar, then click Inspect particle.", id="particle-detail-status", className="status"),
                            html.Pre("{}", id="particle-detail-json", className="json-pre"),
                        ],
                    ),
                ],
            ),
        ],
    )


def metadata_page(payload: Dict[str, Any]) -> html.Div:
    options = _event_options(payload)
    default_value = options[0]["value"] if options else None
    return html.Div(
        className="content",
        children=[
            card(
                "Metadata explorer",
                "event-level JSON",
                [
                    html.Div("Event", className="label"),
                    dcc.Dropdown(id="metadata-event-select", options=options, value=default_value, clearable=False if options else True),
                    html.Div(id="metadata-summary", className="status", style={"marginTop": "10px"}),
                ],
            ),
            html.Div(
                className="grid",
                style={"gridTemplateColumns": "1fr 1fr"},
                children=[
                    card("Storage metadata", "before/after sizes", [html.Pre("{}", id="storage-metadata-json", className="json-pre")]),
                    card("Bundle metadata", "frames and memory", [html.Pre("{}", id="bundle-metadata-json", className="json-pre")]),
                    card("MadGraph metadata", "cards + scan + seed", [html.Pre("{}", id="madgraph-metadata-json", className="json-pre")]),
                    card("Scan metadata", "params + widths", [html.Pre("{}", id="scan-metadata-json", className="json-pre")]),
                ],
            ),
        ],
    )


def empty_page() -> html.Div:
    return html.Div(
        className="content",
        children=[
            status_box("No payload yet. Click Load / Refresh dashboard in the sidebar."),
        ],
    )


def make_app(default_db: str = DEFAULT_DB, default_storage: str = DEFAULT_STORAGE, default_events_root: str = DEFAULT_EVENTS_ROOT) -> Dash:
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.title = "SET-ANUBIS DB dashboard"
    server = app.server

    app.layout = html.Div(
        className="app-shell",
        children=[
            dcc.Store(id="payload-store"),
            html.Div(className="sidebar", children=[controls_sidebar(default_db, default_storage, default_events_root, app.get_asset_url("set-anubis-logo.png"))]),
            html.Div(
                className="content",
                children=[
                    dcc.Tabs(
                        id="page-tabs",
                        value="overview",
                        className="tabbar",
                        parent_className="tabbar",
                        children=[
                            dcc.Tab(label="Overview", value="overview", className="tab", selected_className="tab--selected"),
                            dcc.Tab(label="Storage", value="storage", className="tab", selected_className="tab--selected"),
                            dcc.Tab(label="Events", value="events", className="tab", selected_className="tab--selected"),
                            dcc.Tab(label="Particles", value="particles", className="tab", selected_className="tab--selected"),
                            dcc.Tab(label="Metadata", value="metadata", className="tab", selected_className="tab--selected"),
                        ],
                    ),
                    html.Div(id="page-content", children=empty_page()),
                ],
            ),
        ],
    )

    @app.callback(
        Output("payload-store", "data"),
        Output("status-line", "children"),
        Output("model-filter", "options"),
        Input("refresh-btn", "n_clicks"),
        Input("backfill-btn", "n_clicks"),
        State("db-path", "value"),
        State("storage-dir", "value"),
        State("events-root", "value"),
        State("model-filter", "value"),
        State("llp-pid-filter", "value"),
        State("bundle-filter", "value"),
        State("event-limit", "value"),
        State("include-particles", "value"),
    )
    def load_or_backfill(refresh_clicks, backfill_clicks, db_path, storage_dir, events_root, model, llp_pid, bundle_filter, event_limit, include_particles):
        trigger = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else "refresh-btn"
        db_path = str(db_path or "").strip()
        storage_dir = str(storage_dir or "").strip()
        events_root = str(events_root or "").strip()
        if not db_path or not storage_dir:
            return no_update, "Missing DB path or storage dir.", no_update
        try:
            if trigger == "backfill-btn":
                if not events_root:
                    return no_update, "Missing Events root for backfill.", no_update
                res = dbdata.refresh_storage_metadata(db_path, storage_dir, events_root, dry_run=False)
                ok = sum(1 for r in res if r.get("ok"))
                ko = len(res) - ok
                backfill_msg = f"Backfill storage metadata: {ok} ok, {ko} failed.\n"
            else:
                backfill_msg = ""

            payload = dbdata.load_payload(
                db_path,
                storage_dir,
                model=model,
                llp_pid=_int_or_none(llp_pid),
                has_bundle=_bool_from_dropdown(bundle_filter),
                limit=_int_or_none(event_limit) or 500,
                include_particles="yes" in (include_particles or []),
            )
            payload = dbdata.recompute_payload_storage_rollups(payload)
            status = (
                backfill_msg
                + f"Loaded {len(payload.get('events') or [])} events from {db_path}\n"
                + f"CAS: {human_bytes((payload.get('storage') or {}).get('cas_size_bytes'))} • "
                + f"Bundles: {human_bytes((payload.get('storage') or {}).get('stored_bundle_size_bytes'))}"
            )
            return payload, status, _model_options(payload)
        except Exception as exc:
            return no_update, f"ERROR: {exc}\n\n{traceback.format_exc(limit=8)}", no_update

    @app.callback(Output("page-content", "children"), Input("page-tabs", "value"), Input("payload-store", "data"))
    def render_page(tab, payload):
        if not payload:
            return empty_page()
        if tab == "storage":
            return storage_page(payload)
        if tab == "events":
            return events_page(payload)
        if tab == "particles":
            return particles_page(payload)
        if tab == "metadata":
            return metadata_page(payload)
        return overview_page(payload)

    @app.callback(
        Output("selected-event-summary", "children"),
        Output("selected-event-json", "children"),
        Input("events-table", "selected_rows"),
        State("events-table", "data"),
        State("db-path", "value"),
        State("storage-dir", "value"),
        prevent_initial_call=True,
    )
    def show_selected_event(selected_rows, table_data, db_path, storage_dir):
        if not selected_rows or not table_data:
            raise PreventUpdate
        row = table_data[selected_rows[0]]
        event_id = row.get("id")
        if not event_id:
            raise PreventUpdate
        try:
            detail = dbdata.get_event_detail(db_path, storage_dir, event_id)
            storage = detail.get("storage_metadata") or {}
            comparison = storage.get("comparison") or {}
            summary = (
                f"Event {event_id}\n"
                f"Run: {detail.get('run_name')} • pre-decay: {detail.get('pre_decay_run_name')}\n"
                f"Model: {detail.get('model')} • seed: {detail.get('seed')} • LLP: {detail.get('llp_pid')}\n"
                f"Source HEPMC: {human_bytes(detail.get('source_hepmc_size_bytes'))} • bundle: {human_bytes(detail.get('stored_bundle_size_bytes'))}\n"
                f"Bundle/original: {human_percent(comparison.get('bundle_over_original_runs'))}"
            )
            return summary, pretty_json(detail)
        except Exception as exc:
            return f"ERROR while loading event {event_id}: {exc}", "{}"

    @app.callback(
        Output("particle-detail-status", "children"),
        Output("particle-detail-json", "children"),
        Input("particle-btn", "n_clicks"),
        State("particle-pdg", "value"),
        State("particle-max-channels", "value"),
        State("model-filter", "value"),
        State("db-path", "value"),
        State("storage-dir", "value"),
        prevent_initial_call=True,
    )
    def inspect_particle(n_clicks, pdg_value, max_channels, model, db_path, storage_dir):
        pdg = _int_or_none(pdg_value)
        if pdg is None:
            return "Invalid PDG.", "{}"
        try:
            info = dbdata.get_particle_detail(db_path, storage_dir, pdg, model=model, max_channels=_int_or_none(max_channels) or 50)
            if not info:
                return f"PDG {pdg} not found in stored banners for current filter.", "{}"
            status = (
                f"PDG {pdg} • {info.get('name') or 'unknown'}\n"
                f"mass={human_number(info.get('mass'))} • width={human_number(info.get('width'))} • "
                f"charge={human_number(info.get('charge'))} • spin={human_number(info.get('spin'))}\n"
                f"occurrences={len(info.get('occurrences') or [])}"
            )
            return status, pretty_json(info)
        except Exception as exc:
            return f"ERROR while reading particle {pdg}: {exc}", "{}"

    @app.callback(
        Output("metadata-summary", "children"),
        Output("storage-metadata-json", "children"),
        Output("bundle-metadata-json", "children"),
        Output("madgraph-metadata-json", "children"),
        Output("scan-metadata-json", "children"),
        Input("metadata-event-select", "value"),
        State("db-path", "value"),
        State("storage-dir", "value"),
        prevent_initial_call=True,
    )
    def show_metadata(event_id, db_path, storage_dir):
        if not event_id:
            raise PreventUpdate
        try:
            detail = dbdata.get_event_detail(db_path, storage_dir, event_id)
            summary = (
                f"{detail.get('run_name')} • {detail.get('model')}\n"
                f"xsec={human_number(detail.get('cross_section'))} pb • seed={detail.get('seed')}\n"
                f"bundle={human_bytes(detail.get('stored_bundle_size_bytes'))} • source={human_bytes(detail.get('source_hepmc_size_bytes'))}"
            )
            scan = {"params": detail.get("scan_params") or {}, "widths": detail.get("scan_widths") or {}}
            return (
                summary,
                pretty_json(detail.get("storage_metadata") or {}),
                pretty_json(detail.get("bundle_metadata") or {}),
                pretty_json(detail.get("madgraph_metadata") or {}),
                pretty_json(scan),
            )
        except Exception as exc:
            return f"ERROR: {exc}", "{}", "{}", "{}", "{}"

    app.server = server
    return app


app = make_app()
server = app.server


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="SetAnubis EventDatabase Dash monitor")
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite database path")
    parser.add_argument("--storage", default=DEFAULT_STORAGE, help="CAS/Event storage directory")
    parser.add_argument("--events-root", default=DEFAULT_EVENTS_ROOT, help="MadGraph Events root, used by backfill")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    local_app = make_app(args.db, args.storage, args.events_root)
    local_app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
