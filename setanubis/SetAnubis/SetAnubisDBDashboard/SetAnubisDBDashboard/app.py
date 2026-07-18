import argparse
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from SetAnubis.branding import show_banner

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
from .demo import ensure_demo_workspace

_DEMO_WORKSPACE = ensure_demo_workspace()
DEFAULT_DB = os.environ.get("SETANUBIS_DB_PATH", str(_DEMO_WORKSPACE.database))
DEFAULT_STORAGE = os.environ.get("SETANUBIS_STORAGE_DIR", str(_DEMO_WORKSPACE.storage))
DEFAULT_EVENTS_ROOT = os.environ.get("SETANUBIS_EVENTS_ROOT", str(_DEMO_WORKSPACE.events_root))


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
        metric("Generated samples", human_number(storage.get("events")), f"selection-ready bundles: {human_number(storage.get('events_with_bundles'))}"),
        metric("UFO models", human_number(storage.get("models")), f"retained HepMC records: {human_number(storage.get('events_with_stored_hepmc'))}"),
        metric("CAS footprint", human_bytes(storage.get("cas_size_bytes")), f"content-addressed blobs: {human_number(storage.get('cas_blobs'))}"),
        metric("Generator folders", human_bytes(storage.get("original_runs_total_size_bytes")), "pre-decay and decayed runs"),
        metric("Compact bundles", human_bytes(storage.get("stored_bundle_size_bytes")), f"bundle/folders: {human_percent(ratio_original)}", "good" if ratio_original is not None and ratio_original < 0.5 else ""),
        metric("Storage reduction", human_bytes(saved_original), "relative to generator folders", "good" if saved_original and saved_original > 0 else ""),
    ]


def controls_sidebar(default_db: str, default_storage: str, default_events_root: str, logo_src: str, initial_profile: str = "demo") -> html.Div:
    return html.Div(
        className="sidebar-stack",
        children=[
            html.Div(
                className="brand scientific-brand",
                children=[
                    html.Img(src=logo_src, alt="SET-ANUBIS logo", className="brand-logo"),
                    html.Div(
                        className="brand-copy",
                        children=[
                            html.H1("Campaign database inspector"),
                            html.Div(
                                "Generator provenance, scan metadata and compact selection bundles.",
                                className="brand-subtitle",
                            ),
                        ],
                    ),
                    html.Div("SET-ANUBIS", className="badge"),
                ],
            ),
            html.Div(
                className="science-note",
                children=[
                    html.Strong("Purpose. "),
                    "Audit the transition from generated MadGraph/Pythia samples to selection-ready data products without modifying the campaign database.",
                ],
            ),
            card(
                "Campaign source",
                "SQLite metadata and content-addressed storage",
                [
                    html.Div("Workspace", className="label"),
                    dcc.Dropdown(
                        id="database-profile",
                        options=[
                            {"label": "Packaged HNL CPC benchmark", "value": "demo"},
                            {"label": "Local SET-ANUBIS campaign", "value": "custom"},
                        ],
                        value=initial_profile,
                        clearable=False,
                    ),
                    html.Div(
                        "The packaged workspace is created from the versioned R5 HepMC sample, compact bundle and selection manifest.",
                        id="database-profile-note",
                        className="hint",
                    ),
                    html.Div("Event database", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="db-path", type="text", value=default_db, style={"width": "100%"}),
                    html.Div("Content-addressed storage", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="storage-dir", type="text", value=default_storage, style={"width": "100%"}),
                    html.Div("MadGraph Events/ root", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="events-root", type="text", value=default_events_root, style={"width": "100%"}),
                    html.Button("Load campaign summary", id="refresh-btn", n_clicks=0, className="primary-action"),
                    html.Button(
                        "Refresh storage provenance from Events/",
                        id="backfill-btn",
                        n_clicks=0,
                        className="secondary-btn",
                        style={"marginTop": "8px"},
                    ),
                    html.Div(id="status-line", className="status scientific-status"),
                ],
                className="card control-card",
            ),
            card(
                "Scientific filters",
                "applied when the campaign is loaded",
                [
                    html.Div("UFO model", className="label"),
                    dcc.Dropdown(id="model-filter", options=[], value=None, clearable=True, placeholder="All stored models"),
                    html.Div("LLP PDG identifier", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="llp-pid-filter", type="text", value="", placeholder="9900012", style={"width": "100%"}),
                    html.Div("Selection-ready bundle", className="label", style={"marginTop": "10px"}),
                    dcc.Dropdown(
                        id="bundle-filter",
                        options=[
                            {"label": "All generated samples", "value": "all"},
                            {"label": "Only samples with a compact bundle", "value": "yes"},
                            {"label": "Only samples awaiting bundle preparation", "value": "no"},
                        ],
                        value="all",
                        clearable=False,
                    ),
                    html.Div("Maximum samples", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="event-limit", type="text", value="500", style={"width": "100%"}),
                    dcc.Checklist(
                        id="include-particles",
                        options=[{"label": "Parse particle properties and decay tables from stored banners", "value": "yes"}],
                        value=["yes"],
                        className="checklist",
                    ),
                ],
                className="card control-card",
            ),
            card(
                "Particle record",
                "SLHA information retained in generator banners",
                [
                    html.Div("PDG identifier", className="label"),
                    dcc.Input(id="particle-pdg", type="text", value="9900012", style={"width": "100%"}),
                    html.Div("Maximum decay channels", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="particle-max-channels", type="text", value="25", style={"width": "100%"}),
                    html.Button("Inspect particle record", id="particle-btn", n_clicks=0, className="secondary-btn", style={"marginTop": "10px"}),
                ],
                className="card control-card",
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
                    graph_card("Generated samples by model", dcc.Graph(figure=events_by_model(payload.get("models") or []), style={"height": "35vh"}), "stored generator samples"),
                    graph_card("Campaign ingestion timeline", dcc.Graph(figure=import_timeline(payload.get("events") or []), style={"height": "35vh"}), "database insertion date"),
                ],
            ),
            html.Div(
                className="graph-row",
                children=[
                    graph_card("Generated cross-section", dcc.Graph(figure=cross_section_hist(payload.get("events") or []), style={"height": "32vh"}), "pb"),
                    graph_card("Parameter-scan projection", dcc.Graph(figure=scan_scatter(payload.get("events") or []), style={"height": "32vh"}), "first available numerical scan coordinate"),
                    graph_card("Selection-bundle composition", dcc.Graph(figure=bundle_frames(payload.get("bundle_frames") or {}), style={"height": "32vh"}), "rows retained in each DataFrame"),
                ],
            ),
        ],
    )


def storage_page(payload: Dict[str, Any]) -> html.Div:
    return html.Div(
        className="content",
        children=[
            metrics_row([
                metric("Source HepMC records", human_bytes((payload.get("storage") or {}).get("source_hepmc_size_bytes")), "sum over generated samples"),
                metric("Generator run folders", human_bytes((payload.get("storage") or {}).get("original_runs_total_size_bytes")), "pre-decay and decayed directories"),
                metric("Selection-ready bundles", human_bytes((payload.get("storage") or {}).get("stored_bundle_size_bytes")), "compact DataFrame collections", "good"),
                metric("Bundle / HepMC", human_percent((payload.get("storage") or {}).get("bundle_over_source_hepmc")), "storage ratio"),
                metric("Bundle / folders", human_percent((payload.get("storage") or {}).get("bundle_over_original_runs")), "storage ratio"),
            ]),
            html.Div(
                className="graph-row-2",
                children=[
                    graph_card("Campaign storage composition", dcc.Graph(figure=storage_breakdown(payload.get("storage") or {}), style={"height": "38vh"}), "logical and content-addressed products"),
                    graph_card("Provenance artifacts", dcc.Graph(figure=artifact_sizes(payload.get("artifacts") or []), style={"height": "38vh"}), "files retained in content-addressed storage"),
                ],
            ),
            html.Div(
                className="graph-row",
                children=[
                    graph_card("Per-sample storage", dcc.Graph(figure=per_event_storage(payload.get("events") or []), style={"height": "36vh"}), "generator folders versus compact bundle"),
                    graph_card("Bundle reduction factor", dcc.Graph(figure=storage_ratio_hist(payload.get("events") or []), style={"height": "36vh"}), "compact bundle divided by generator folders"),
                    graph_card("Storage grouped by UFO model", dcc.Graph(figure=model_storage(payload.get("models") or []), style={"height": "36vh"}), "source, generator and bundle footprints"),
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
                    card("Generated samples", f"{len(table_rows)} records", [data_table("events-table", columns, table_rows, page_size=14, row_selectable="single")]),
                    card(
                        "Selected generated sample",
                        "provenance and storage metadata",
                        [
                            html.Div("Select one generated sample in the table.", id="selected-event-summary", className="status"),
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
            status_box("Load the packaged benchmark or select a local campaign database from the sidebar."),
        ],
    )


def make_app(default_db: str = DEFAULT_DB, default_storage: str = DEFAULT_STORAGE, default_events_root: str = DEFAULT_EVENTS_ROOT) -> Dash:
    app = Dash(
        __name__,
        suppress_callback_exceptions=True,
        assets_folder=str(Path(__file__).with_name("assets")),
    )
    app.title = "SET-ANUBIS campaign database inspector"
    server = app.server

    initial_profile = (
        "demo"
        if Path(default_db) == Path(DEFAULT_DB)
        and Path(default_storage) == Path(DEFAULT_STORAGE)
        else "custom"
    )
    app.layout = html.Div(
        className="app-shell",
        children=[
            dcc.Store(id="payload-store"),
            html.A("Skip to campaign analysis", href="#campaign-workspace", className="skip-link"),
            html.Aside(
                className="sidebar",
                children=[
                    controls_sidebar(
                        default_db,
                        default_storage,
                        default_events_root,
                        app.get_asset_url("set-anubis-logo.png"),
                        initial_profile,
                    )
                ],
            ),
            html.Main(
                id="campaign-workspace",
                className="main-panel",
                children=[
                    html.Div(
                        className="main-navigation",
                        children=[
                            html.Div(children=[
                                html.Div(className="section-kicker", children="SET-ANUBIS campaign workspace"),
                                html.H1("Generated-sample provenance and storage diagnostics"),
                            ]),
                            dcc.Tabs(
                                id="page-tabs",
                                value="overview",
                                className="tabbar page-tabbar",
                                parent_className="tabbar page-tabbar",
                                children=[
                                    dcc.Tab(label="Campaign overview", value="overview", className="tab", selected_className="tab--selected"),
                                    dcc.Tab(label="Storage & provenance", value="storage", className="tab", selected_className="tab--selected"),
                                    dcc.Tab(label="Generated samples", value="events", className="tab", selected_className="tab--selected"),
                                    dcc.Tab(label="Particle model", value="particles", className="tab", selected_className="tab--selected"),
                                    dcc.Tab(label="Metadata records", value="metadata", className="tab", selected_className="tab--selected"),
                                ],
                            ),
                        ],
                    ),
                    html.Div(id="page-content", children=empty_page()),
                ],
            ),
        ],
    )

    @app.callback(
        Output("db-path", "value"),
        Output("storage-dir", "value"),
        Output("events-root", "value"),
        Output("database-profile-note", "children"),
        Output("backfill-btn", "disabled"),
        Input("database-profile", "value"),
        State("db-path", "value"),
        State("storage-dir", "value"),
        State("events-root", "value"),
    )
    def select_database_workspace(profile, current_db, current_storage, current_events_root):
        if profile == "demo":
            return (
                DEFAULT_DB,
                DEFAULT_STORAGE,
                DEFAULT_EVENTS_ROOT,
                "Packaged R5 benchmark: a real SQLite/CAS workspace materialised from the versioned HNL HepMC record, compact bundle and selection manifest.",
                True,
            )
        return (
            current_db if current_db != DEFAULT_DB else "",
            current_storage if current_storage != DEFAULT_STORAGE else "",
            current_events_root if current_events_root != DEFAULT_EVENTS_ROOT else "",
            "Provide the EventDatabase SQLite file, its matching CAS storage directory and, optionally, the MadGraph Events/ root used to refresh storage provenance.",
            False,
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
    show_banner(force=True)
    parser = argparse.ArgumentParser(description="Inspect SET-ANUBIS campaign provenance and compact event bundles")
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite database path (defaults to the packaged HNL benchmark workspace)")
    parser.add_argument("--storage", default=DEFAULT_STORAGE, help="CAS/event storage directory matching the selected database")
    parser.add_argument("--events-root", default=DEFAULT_EVENTS_ROOT, help="MadGraph Events/ root used only for storage-provenance backfill")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    local_app = make_app(args.db, args.storage, args.events_root)
    local_app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
