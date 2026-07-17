from __future__ import annotations

import os
import json
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

px.defaults.template = "plotly_dark"
px.defaults.color_discrete_sequence = px.colors.qualitative.Set2

from dash import Dash, dcc, html, Input, Output, State, no_update
from dash import dash_table

from SetAnubis.HepMCGUI.defineGeometry import ATLASCavern

from SetAnubis.HepMCGUI.bsm_analysis.sources import HepMCFileSource
from SetAnubis.HepMCGUI.bsm_analysis.extractor import ParticleExtractor, ExtractionConfig
from SetAnubis.HepMCGUI.bsm_analysis.filters import ParticleFilterSpec, Range, apply_filters
from SetAnubis.HepMCGUI.bsm_analysis.event_reader import load_event_from_hepmc
from SetAnubis.HepMCGUI.bsm_analysis.track_builder import TrackBuildConfig, build_event_tracks, TrackSegment
from SetAnubis.HepMCGUI.bsm_analysis.lifetime import add_lifetime_columns, lifetime_column_for_mode, event_lifetime_column_for_mode, lifetime_label_for_mode

from SetAnubis.HepMCGUI.geometry.cavern import CavernTransform
from SetAnubis.HepMCGUI.geometry.plotly_cavern import CavernFigureFactory
from SetAnubis.HepMCGUI.geometry.plotly_cavern_3d import Cavern3DFigureFactory
from SetAnubis.HepMCGUI.geometry.anubis_plotly import AnubisOverlayFactory
from SetAnubis.HepMCGUI.geometry.region_classifier import RegionClassifier


def _int_or_none(v: Any) -> Optional[int]:
    try:
        if v is None or str(v).strip() == "":
            return None
        return int(str(v).strip())
    except Exception:
        return None


def _float_or_none(v: Any) -> Optional[float]:
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(str(v).strip())
    except Exception:
        return None


def make_range(lo: Any, hi: Any) -> Range:
    return Range(lo=_float_or_none(lo), hi=_float_or_none(hi))


cav = ATLASCavern()

# Ceiling-like stations (simple RPC shells attached to the vault)
ANUBIS_CEILING_RPCs = cav.createSimpleRPCs(
    [cav.archRadius - 0.2, cav.archRadius - 0.6, cav.archRadius - 1.2],
    RPCthickness=0.06,
)

# Shaft stations (ANUBIS) — signature matches defineGeometry.createShaftRPCs:
#   createShaftRPCs(heights, RPCradius={...}, RPCthickness=..., clearance=..., pipeCutoff={...}, shafts=[...], includeCone=...)
ANUBIS_SHAFT_RPCs = cav.createShaftRPCs(
    [0, 1, 18.5, 19.5, 37, 38, 55.5, 56.5],
    RPCradius={"PX14": -1, "PX16": -1},
    RPCthickness=0.06,
    clearance=0.25,
    pipeCutoff={"x": -7.25, "z": ""},
    shafts=["PX14", "PX16"],
    includeCone=False,
)

fig_factory_2d = CavernFigureFactory(cavern=cav)
fig_factory_3d = Cavern3DFigureFactory(cavern=cav)
anubis_factory = AnubisOverlayFactory(cavern=cav)
classifier = RegionClassifier(cavern=cav)


def _fig_style(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=12, r=12, t=46, b=12),
        font=dict(color="rgba(229,231,235,0.92)"),
    )
    return fig


def make_hist(df: pd.DataFrame, col: str, title: str) -> go.Figure:
    if df.empty or col not in df.columns:
        return _fig_style(go.Figure(), f"{title} (no data)")
    fig = px.histogram(df, x=col, nbins=60)
    return _fig_style(fig, title)


def make_relations_bar(df: pd.DataFrame, col: str, title: str, top_n: int = 15) -> go.Figure:
    if df.empty or col not in df.columns:
        return _fig_style(go.Figure(), f"{title} (no data)")
    exploded = df[col].explode()
    exploded = exploded[~exploded.isna()]
    if exploded.empty:
        return _fig_style(go.Figure(), f"{title} (no data)")
    counts = exploded.value_counts().head(top_n).reset_index()
    counts.columns = ["pdg", "count"]

    try:
        from bsm_analysis.particle_info import particle_display_name
        counts["label"] = counts["pdg"].apply(lambda pid: f"{particle_display_name(int(pid))} ({int(pid)})")
    except Exception:
        counts["label"] = counts["pdg"].apply(lambda pid: str(int(pid)))

    fig = px.bar(counts, x="label", y="count")
    fig.update_xaxes(tickangle=35)
    return _fig_style(fig, title)


def overlay_vertices(
    fig: go.Figure,
    df: pd.DataFrame,
    plane: str,
    show_prod: bool,
    show_dec: bool,
    max_points: int = 25000,
) -> go.Figure:
    if df.empty:
        return fig

    d = df
    if len(d) > max_points:
        d = d.sample(max_points, random_state=0)

    def add_points(tag: str, xs: pd.Series, ys: pd.Series, color: str):
        msk = np.isfinite(xs.to_numpy()) & np.isfinite(ys.to_numpy())
        if not np.any(msk):
            return
        fig.add_trace(
            go.Scattergl(
                x=xs.to_numpy()[msk],
                y=ys.to_numpy()[msk],
                mode="markers",
                marker=dict(size=6, color=color),
                name=tag,
                hovertemplate=f"{tag}<br>x=%{{x:.3f}} m<br>y=%{{y:.3f}} m<br>event=%{{customdata[0]}}<extra></extra>",
                customdata=np.stack([d["event"].to_numpy()[msk]], axis=1),
                showlegend=False,
            )
        )

    if plane == "XY":
        if show_prod:
            add_points("production", d["prod_x_m"], d["prod_y_m"], "rgba(167,139,250,0.90)")
        if show_dec:
            add_points("decay", d["dec_x_m"], d["dec_y_m"], "rgba(96,165,250,0.90)")
    elif plane == "XZ":
        if show_prod:
            add_points("production", d["prod_x_m"], d["prod_z_m"], "rgba(167,139,250,0.90)")
        if show_dec:
            add_points("decay", d["dec_x_m"], d["dec_z_m"], "rgba(96,165,250,0.90)")
    elif plane == "ZY":
        if show_prod:
            add_points("production", d["prod_z_m"], d["prod_y_m"], "rgba(167,139,250,0.90)")
        if show_dec:
            add_points("decay", d["dec_z_m"], d["dec_y_m"], "rgba(96,165,250,0.90)")

    return fig


COL_ROOT = "rgba(251,113,133,0.90)"   # pink
COL_CHARGED = "rgba(52,211,153,0.72)" # mint
COL_NEUTRAL = "rgba(148,163,184,0.42)"# slate
COL_UNKNOWN = "rgba(226,232,240,0.55)"


def _seg_color(seg: TrackSegment) -> str:
    if seg.is_root:
        return COL_ROOT
    if seg.charged is None:
        return COL_UNKNOWN
    return COL_CHARGED if seg.charged else COL_NEUTRAL


def add_tracks_2d(fig: go.Figure, segs: List[Dict[str, Any]], plane: str, show_labels: bool = False) -> go.Figure:
    if not segs:
        return fig

    # build multi-segment traces grouped by color bucket
    buckets: Dict[str, Dict[str, list]] = {}

    def bucket_for(color: str):
        if color not in buckets:
            buckets[color] = {"x": [], "y": [], "text": []}
        return buckets[color]

    for s in segs:
        color = s["color"]
        b = bucket_for(color)

        if plane == "XY":
            x0, y0, x1, y1 = s["x0"], s["y0"], s["x1"], s["y1"]
        elif plane == "XZ":
            x0, y0, x1, y1 = s["x0"], s["z0"], s["x1"], s["z1"]
        else:  # ZY
            x0, y0, x1, y1 = s["z0"], s["y0"], s["z1"], s["y1"]

        hover = f'{s["name"]} (PDG {s["pid"]})<br>depth={s["depth"]}{"<br>root" if s["is_root"] else ""}'
        b["x"] += [x0, x1, None]
        b["y"] += [y0, y1, None]
        b["text"] += [hover, hover, None]

        if show_labels:
            xm, ym = (x0 + x1) * 0.5, (y0 + y1) * 0.5
            fig.add_trace(go.Scattergl(
                x=[xm], y=[ym], mode="text",
                text=[s["name"]],
                textfont=dict(size=11, color="rgba(229,231,235,0.85)"),
                showlegend=False,
                hoverinfo="skip",
            ))

    for color, b in buckets.items():
        fig.add_trace(
            go.Scattergl(
                x=b["x"],
                y=b["y"],
                mode="lines",
                line=dict(width=2, color=color),
                opacity=0.95,
                hoverinfo="text",
                text=b["text"],
                showlegend=False,
            )
        )
    return fig


def add_tracks_3d(fig: go.Figure, segs: List[Dict[str, Any]], show_labels: bool = False) -> go.Figure:
    if not segs:
        return fig

    buckets: Dict[str, Dict[str, list]] = {}

    def bucket_for(color: str):
        if color not in buckets:
            buckets[color] = {"x": [], "y": [], "z": [], "text": []}
        return buckets[color]

    for s in segs:
        color = s["color"]
        b = bucket_for(color)
        hover = f'{s["name"]} (PDG {s["pid"]})<br>depth={s["depth"]}{"<br>root" if s["is_root"] else ""}'
        b["x"] += [s["x0"], s["x1"], None]
        b["y"] += [s["y0"], s["y1"], None]
        b["z"] += [s["z0"], s["z1"], None]
        b["text"] += [hover, hover, None]

        if show_labels:
            xm = (s["x0"] + s["x1"]) * 0.5
            ym = (s["y0"] + s["y1"]) * 0.5
            zm = (s["z0"] + s["z1"]) * 0.5
            fig.add_trace(go.Scatter3d(
                x=[xm], y=[ym], z=[zm], mode="text",
                text=[s["name"]],
                textfont=dict(size=10, color="rgba(229,231,235,0.85)"),
                showlegend=False,
                hoverinfo="skip",
            ))

    for color, b in buckets.items():
        fig.add_trace(
            go.Scatter3d(
                x=b["x"], y=b["y"], z=b["z"],
                mode="lines",
                line=dict(width=4, color=color),
                opacity=0.95,
                hoverinfo="text",
                text=b["text"],
                showlegend=False,
            )
        )
    return fig


REGION_ORDER = ["anubis", "atlas", "cavern", "outside", "stable", "unknown"]


def classify_rows_region(df: pd.DataFrame) -> pd.Series:
    """
    Classify each row according to its decay vertex region.
    """
    if df.empty:
        return pd.Series([], dtype=str)

    x = df["dec_x_m"].to_numpy(dtype=float)
    y = df["dec_y_m"].to_numpy(dtype=float)
    z = df["dec_z_m"].to_numpy(dtype=float)

    finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)

    out = np.full(len(df), "stable", dtype=object)
    out[~finite] = "stable"

    if finite.any():
        xf, yf, zf = x[finite], y[finite], z[finite]
        in_an = classifier.in_anubis_shaft(xf, yf, zf, ANUBIS_SHAFT_RPCs) | classifier.in_anubis_ceiling_simple(xf, yf, zf, ANUBIS_CEILING_RPCs)
        in_at = classifier.in_atlas(xf, yf, zf, tracking_only=False)
        in_ca = classifier.in_cavern(xf, yf, zf)
        lab = np.full(xf.shape[0], "outside", dtype=object)
        lab[in_ca] = "cavern"
        lab[in_at] = "atlas"
        lab[in_an] = "anubis"
        out[finite] = lab

    return pd.Series(out, index=df.index, dtype=str)


def build_events_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate per-event summary used by the Event-by-event page and global filters.
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "event", "n_bsm", "region",
            "lifetime_proper_ns_max", "lifetime_lab_ns_max",
            "met", "pt_max", "E_max",
        ])

    d = add_lifetime_columns(df.copy())
    if "region" not in d.columns:
        d["region"] = classify_rows_region(d)

    agg = d.groupby("event").agg(
        n_bsm=("pid", "size"),
        region=("region", lambda s: next((r for r in REGION_ORDER if (s == r).any()), "unknown")),
        lifetime_proper_ns_max=("lifetime_proper_ns", "max"),
        lifetime_lab_ns_max=("lifetime_lab_ns", "max"),
        met=("met", "max"),
        pt_max=("pt", "max"),
        E_max=("E", "max"),
    ).reset_index()

    # nicer order
    agg = agg.sort_values(["event"]).reset_index(drop=True)
    return agg


app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    assets_folder=str(Path(__file__).with_name("assets")),
)
app.title = "SET-ANUBIS HepMC explorer"
server = app.server


def controls_sidebar(logo_src: str) -> html.Div:
    def range_row(lbl: str, lo_id: str, hi_id: str):
        return html.Div(
            className="row-3",
            children=[
                html.Div(lbl, className="label"),
                dcc.Input(id=lo_id, type="text", placeholder="min"),
                dcc.Input(id=hi_id, type="text", placeholder="max"),
            ],
        )

    return html.Div(
        className="grid",
        children=[
            html.Div(className="brand", children=[
                html.Img(src=logo_src, alt="SET-ANUBIS logo", className="brand-logo"),
                html.Div(className="brand-copy", children=[
                    html.H1("SET-ANUBIS HepMC explorer"),
                    html.Div("Inspect LLP decays in the ATLAS cavern and ANUBIS geometry.", className="brand-subtitle"),
                ]),
                html.Div("Dash", className="badge"),
            ]),

            html.Div(
                className="card",
                children=[
                    html.Div("HepMC path", className="label"),
                    dcc.Input(id="hepmc-path", type="text", value="tag_1_pythia8_events.hepmc", style={"width": "100%"}),
                    html.Hr(),

                    html.Div("Data source", className="label"),
                    dcc.Dropdown(
                        id="source-kind",
                        options=[
                            {"label": "HepMC file", "value": "hepmc"},
                            {"label": "CSV/DataFrame (placeholder)", "value": "csv"},
                        ],
                        value="hepmc",
                        clearable=False,
                    ),
                    html.Div(id="csv-hint", style={"fontSize": "12px", "opacity": 0.85, "marginTop": "6px"}),
                ],
            ),

            html.Div(
                className="card",
                children=[
                    html.Div("PDG ID", className="label"),
                    dcc.Input(id="pdg-id", type="text", value="9000005"),

                    html.Div(className="row", children=[html.Div("max_events", className="label"), dcc.Input(id="max-events", type="text", value="")]),
                    html.Div(className="row", children=[html.Div("status", className="label"), dcc.Input(id="status", type="text", value="")]),

                    html.Hr(),
                    html.Div("Lifetime display", className="label"),
                    dcc.RadioItems(
                        id="lifetime-mode",
                        options=[
                            {"label": "proper time", "value": "proper"},
                            {"label": "lab time", "value": "lab"},
                        ],
                        value="proper",
                        className="checklist",
                    ),

                    dcc.Checklist(
                        id="ignore-self-decays",
                        options=[{"label": "ignore self decays (pid→pid)", "value": "yes"}],
                        value=["yes"],
                        className="checklist",
                    ),

                    html.Hr(),
                    html.Div("Event selection (by BSM decay)", className="label"),
                    dcc.Dropdown(
                        id="event-region-filter",
                        options=[
                            {"label": "All events", "value": "all"},
                            {"label": "Only BSM decays outside ATLAS", "value": "outside_atlas"},
                            {"label": "Only BSM decays in ANUBIS", "value": "anubis"},
                        ],
                        value="all",
                        clearable=False,
                    ),

                    html.Hr(),
                    html.Div("Coordinate convention", className="label"),
                    dcc.Checklist(
                        id="pos-is-ip",
                        options=[{"label": "HepMC positions are IP-relative (convert to cavern centre)", "value": "ip"}],
                        value=["ip"],
                        className="checklist",
                    ),

                    html.Button("Run / Refresh", id="run-btn", n_clicks=0),
                    html.Div(id="status-line", className="status"),
                ],
            ),

            html.Div(
                className="card",
                children=[
                    html.Div("Topology filters (BSM rows)", className="label"),
                    html.Div(className="row", children=[html.Div("mother pid", className="label"), dcc.Input(id="mother-pid", type="text", value="")]),
                    html.Div(className="row", children=[html.Div("child pid", className="label"), dcc.Input(id="child-pid", type="text", value="")]),

                    html.Hr(),
                    html.Div("Kinematics filters (BSM rows)", className="label"),
                    range_row("E", "E-lo", "E-hi"),
                    range_row("pT", "pt-lo", "pt-hi"),
                    range_row("|p|", "p-lo", "p-hi"),
                    range_row("px", "px-lo", "px-hi"),
                    range_row("py", "py-lo", "py-hi"),
                    range_row("pz", "pz-lo", "pz-hi"),
                    range_row("eta", "eta-lo", "eta-hi"),
                    range_row("phi", "phi-lo", "phi-hi"),
                    range_row("theta", "theta-lo", "theta-hi"),
                    range_row("MET", "met-lo", "met-hi"),
                ],
            ),

            html.Div(
                className="card",
                children=[
                    html.Div("Geometry options", className="label"),
                    dcc.Dropdown(
                        id="plane",
                        options=[{"label": "XY", "value": "XY"}, {"label": "XZ", "value": "XZ"}, {"label": "ZY", "value": "ZY"}],
                        value="ZY",
                        clearable=False,
                    ),
                    dcc.Checklist(
                        id="geom-options",
                        options=[
                            {"label": "ATLAS envelope", "value": "atlas"},
                            {"label": "acceptance rays", "value": "acc"},
                            {"label": "ANUBIS ceiling", "value": "an_ceiling"},
                            {"label": "ANUBIS shaft", "value": "an_shaft"},
                        ],
                        value=["atlas", "an_ceiling", "an_shaft"],
                        className="checklist",
                    ),
                    dcc.Checklist(
                        id="vertex-options",
                        options=[
                            {"label": "show production vertices", "value": "prod"},
                            {"label": "show decay vertices", "value": "dec"},
                        ],
                        value=["prod", "dec"],
                        className="checklist",
                    ),

                    html.Hr(),
                    html.Div("Decay-tree tracks (filtered events only)", className="label"),
                    dcc.Checklist(
                        id="tree-options",
                        options=[
                            {"label": "overlay SM decay-tree tracks (sampled)", "value": "tree"},
                            {"label": "labels (event view recommended)", "value": "labels"},
                        ],
                        value=[],
                        className="checklist",
                    ),
                    html.Div(className="row", children=[
                        html.Div("depth", className="label"),
                        dcc.Input(id="tree-depth", type="text", value="2"),
                    ]),
                    html.Div(className="row", children=[
                        html.Div("max events", className="label"),
                        dcc.Input(id="tree-max-events", type="text", value="40"),
                    ]),
                ],
            ),
        ],
    )


def overview_page() -> html.Div:
    return html.Div(
        className="content",
        children=[
            html.Div(id="region-metrics", className="metrics-row"),
            html.Div(
                className="grid",
                children=[
                    html.Div(
                        className="card graph-card",
                        children=[
                            html.Div(className="card-title", children=[html.H2("Geometry"), html.Span("2D projections + 3D context")]),
                            dcc.Tabs(
                                id="geom-tabs",
                                value="2d",
                                className="tabbar",
                                parent_className="tabbar",
                                children=[
                                    dcc.Tab(label="2D (XY/XZ/ZY)", value="2d", className="tab", selected_className="tab--selected"),
                                    dcc.Tab(label="3D", value="3d", className="tab", selected_className="tab--selected"),
                                ],
                            ),
                            html.Div([dcc.Loading(dcc.Graph(id="geom-graph", style={"height": "62vh"}), type="dot")], id="geom-2d-wrap"),
                            html.Div([dcc.Loading(dcc.Graph(id="geom-3d", style={"height": "62vh"}), type="dot")], id="geom-3d-wrap", style={"display": "none"}),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="graph-row",
                children=[
                    html.Div(className="card graph-card", children=[html.Div(className="card-title", children=[html.H2("pT"), html.Span("filtered selection")]),
                                                                    dcc.Loading(dcc.Graph(id="hist-pt", style={"height": "32vh"}), type="dot")]),
                    html.Div(className="card graph-card", children=[html.Div(className="card-title", children=[html.H2("eta"), html.Span("filtered selection")]),
                                                                    dcc.Loading(dcc.Graph(id="hist-eta", style={"height": "32vh"}), type="dot")]),
                    html.Div(className="card graph-card", children=[html.Div(className="card-title", children=[html.H2("MET"), html.Span("simple truth")]),
                                                                    dcc.Loading(dcc.Graph(id="hist-met", style={"height": "32vh"}), type="dot")]),
                ],
            ),
            html.Div(
                className="card graph-card",
                children=[
                    html.Div(className="card-title", children=[html.H2("HNL lifetime"), html.Span("selected mode • ns")]),
                    dcc.Loading(dcc.Graph(id="hist-lifetime", style={"height": "32vh"}), type="dot"),
                ],
            ),
            html.Div(
                className="graph-row-2",
                children=[
                    html.Div(className="card graph-card", children=[html.Div(className="card-title", children=[html.H2("Mother PDGs"), html.Span("top 15")]),
                                                                    dcc.Loading(dcc.Graph(id="bar-mothers", style={"height": "36vh"}), type="dot")]),
                    html.Div(className="card graph-card", children=[html.Div(className="card-title", children=[html.H2("Daughter PDGs"), html.Span("top 15")]),
                                                                    dcc.Loading(dcc.Graph(id="bar-children", style={"height": "36vh"}), type="dot")]),
                ],
            ),
        ],
    )


def event_page() -> html.Div:
    return html.Div(
        className="content",
        children=[
            html.Div(
                className="grid",
                children=[
                    html.Div(
                        className="card",
                        children=[
                            html.Div(className="card-title", children=[html.H2("Event-by-event"), html.Span("select an event to draw full topology")]),
                            html.Div(
                                className="event-table-toolbar",
                                children=[
                                    html.Div("quick event filter", className="label"),
                                    dcc.Input(
                                        id="event-number-filter",
                                        type="text",
                                        value="",
                                        placeholder="type 20, 2, cavern…",
                                        debounce=False,
                                        style={"width": "100%"},
                                    ),
                                ],
                            ),
                            html.Div(id="event-help", style={"fontSize": "12px", "opacity": 0.85, "marginBottom": "8px"}),
                            dash_table.DataTable(
                                id="events-table",
                                columns=[
                                    {"name": "event", "id": "event", "type": "numeric"},
                                    {"name": "region", "id": "region", "type": "text"},
                                    {"name": "n_bsm", "id": "n_bsm", "type": "numeric"},
                                    {"name": "HNL lifetime [ns]", "id": "hnl_lifetime_ns", "type": "numeric"},
                                    {"name": "MET", "id": "met", "type": "numeric"},
                                    {"name": "pT max", "id": "pt_max", "type": "numeric"},
                                    {"name": "E max", "id": "E_max", "type": "numeric"},
                                ],
                                data=[],
                                page_action="native",
                                page_current=0,
                                page_size=9,
                                sort_action="native",
                                filter_action="native",
                                filter_options={"case": "insensitive"},
                                row_selectable="single",
                                selected_row_ids=[],
                                style_cell={"fontFamily": "ui-monospace, Menlo, Consolas, monospace", "fontSize": 12, "padding": "8px"},
                                style_table={"overflowX": "auto"},
                            ),
                            html.Div(id="event-summary", className="status", style={"marginTop": "10px"}),
                            html.Div(id="event-decay-tree", className="decay-tree"),
                        ],
                    ),

                    html.Div(
                        className="card graph-card",
                        children=[
                            html.Div(className="card-title", children=[html.H2("Event display"), html.Span("tracks: root + daughters (+ granddaughters)")]),
                            dcc.Tabs(
                                id="event-geom-tabs",
                                value="2d",
                                className="tabbar",
                                parent_className="tabbar",
                                children=[
                                    dcc.Tab(label="2D", value="2d", className="tab", selected_className="tab--selected"),
                                    dcc.Tab(label="3D", value="3d", className="tab", selected_className="tab--selected"),
                                ],
                            ),
                            html.Div([dcc.Loading(dcc.Graph(id="event-geom-2d", style={"height": "62vh"}), type="dot")], id="event-2d-wrap"),
                            html.Div([dcc.Loading(dcc.Graph(id="event-geom-3d", style={"height": "62vh"}), type="dot")], id="event-3d-wrap", style={"display": "none"}),

                            html.Hr(),
                            html.Div("Tracks options (event view)", className="label"),
                            html.Div(className="row", children=[html.Div("depth", className="label"), dcc.Input(id="event-depth", type="text", value="2", debounce=True)]),
                            html.Div(className="row", children=[html.Div("extend [m]", className="label"), dcc.Input(id="event-extend", type="text", value="30", debounce=True)]),
                            html.Button("Apply tracks", id="apply-event-tracks", n_clicks=0, className="secondary-btn"),
                            html.Div("After changing depth or extend, click Apply tracks or press Enter in the field.", className="hint"),
                            dcc.Checklist(
                                id="event-track-options",
                                options=[
                                    {"label": "show labels", "value": "labels"},
                                    {"label": "show only charged", "value": "charged_only"},
                                ],
                                value=["labels"],
                                className="checklist",
                            ),
                        ],
                    ),
                ],
                style={"gridTemplateColumns": "0.85fr 1.15fr"},
            )
        ],
    )


app.layout = html.Div(
    className="app-shell",
    children=[
        dcc.Store(id="df-store"),
        dcc.Store(id="events-store"),
        dcc.Store(id="cfg-store"),
        dcc.Store(id="tracks-store"),

        html.Div(className="sidebar", children=[controls_sidebar(app.get_asset_url("set-anubis-logo.png"))]),

        html.Div(
            className="content",
            children=[
                dcc.Tabs(
                    id="page-tabs",
                    value="overview",
                    className="tabbar",
                    parent_className="tabbar",
                    children=[
                        dcc.Tab(label="Dashboard", value="overview", className="tab", selected_className="tab--selected"),
                        dcc.Tab(label="Event-by-event", value="event", className="tab", selected_className="tab--selected"),
                    ],
                ),
                html.Div(id="overview-wrap", children=overview_page(), style={"display": "block"}),
                html.Div(id="event-wrap", children=event_page(), style={"display": "none"}),
            ],
        ),
    ],
)


@app.callback(
    Output("overview-wrap", "style"),
    Output("event-wrap", "style"),
    Input("page-tabs", "value"),
)
def _toggle_pages(tab: str):
    if tab == "event":
        return {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "none"}



@app.callback(
    Output("geom-2d-wrap", "style"),
    Output("geom-3d-wrap", "style"),
    Input("geom-tabs", "value"),
    prevent_initial_call=True,
)
def _toggle_geom_tabs(tab: str):
    if tab == "3d":
        return {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "none"}


@app.callback(
    Output("event-2d-wrap", "style"),
    Output("event-3d-wrap", "style"),
    Input("event-geom-tabs", "value"),
    prevent_initial_call=True,
)
def _toggle_event_geom_tabs(tab: str):
    if tab == "3d":
        return {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "none"}


@app.callback(Output("csv-hint", "children"), Input("source-kind", "value"))
def _csv_hint(kind: str):
    if kind == "csv":
        return "CSV placeholder: expected columns: event, pid, status, px,py,pz,E, prod_x_m,prod_y_m,prod_z_m,prod_ct_m, dec_x_m,dec_y_m,dec_z_m,dec_ct_m, mother_pids(list/tuple), child_pids(list/tuple), met"
    return ""


@app.callback(
    Output("df-store", "data"),
    Output("events-store", "data"),
    Output("cfg-store", "data"),
    Output("status-line", "children"),
    Input("run-btn", "n_clicks"),
    State("source-kind", "value"),
    State("hepmc-path", "value"),
    State("pdg-id", "value"),
    State("max-events", "value"),
    State("status", "value"),
    State("ignore-self-decays", "value"),
    State("pos-is-ip", "value"),
)
def run_extraction(n_clicks, source_kind, hepmc_path, pdg_id, max_events, status, ignore_self_decays, pos_is_ip):
    if n_clicks is None:
        return no_update, no_update, no_update, no_update

    if source_kind != "hepmc":
        return None, None, None, "CSV/DataFrame source is not implemented yet (interface is ready)."

    if hepmc_path is None or str(hepmc_path).strip() == "":
        return None, None, None, "Missing HepMC path."

    if not os.path.exists(hepmc_path):
        return None, None, None, f"File not found: {hepmc_path}"

    pid = _int_or_none(pdg_id)
    if pid is None:
        return None, None, None, f"Invalid PDG ID: {pdg_id}"

    cav_transform = CavernTransform(cavern=cav, hepmc_positions_are_ip_relative=("ip" in (pos_is_ip or [])))

    src = HepMCFileSource(path=hepmc_path)
    extractor = ParticleExtractor(source=src)

    cfg = ExtractionConfig(
        pdg_id=int(pid),
        max_events=_int_or_none(max_events),
        status=_int_or_none(status),
        ignore_self_decays=("yes" in (ignore_self_decays or [])),
        hepmc_positions_are_ip_relative=("ip" in (pos_is_ip or [])),
        position_transform=cav_transform.to_cavern_centre,
    )

    try:
        df = extractor.extract(cfg)
    except Exception as e:
        return None, None, None, f"Extraction failed: {e}"

    if df.empty:
        return df.to_json(date_format="iso", orient="split"), pd.DataFrame().to_json(orient="split"), json.dumps({"hepmc_path": hepmc_path, "pdg_id": pid}), "No particle rows extracted."

    df = add_lifetime_columns(df)
    df["region"] = classify_rows_region(df)
    events = build_events_table(df)

    # diagnostics
    n_prod = int(np.isfinite(df["prod_x_m"]).sum())
    n_dec = int(np.isfinite(df["dec_x_m"]).sum())
    n_tau = int(np.isfinite(df["lifetime_proper_ns"]).sum()) if "lifetime_proper_ns" in df.columns else 0
    n_tlab = int(np.isfinite(df["lifetime_lab_ns"]).sum()) if "lifetime_lab_ns" in df.columns else 0
    region_counts = events["region"].value_counts().to_dict()

    info = [
        f"Rows extracted: {len(df)}",
        f"Events with ≥1 BSM: {len(events)}",
        f"PDG: {pid} | max_events={_int_or_none(max_events)} | status={_int_or_none(status)}",
        f"Finite production vertices: {n_prod} | Finite decay vertices: {n_dec}",
        f"Finite proper lifetimes: {n_tau} | Finite lab lifetimes: {n_tlab}",
        f"Decay regions: {region_counts}",
    ]

    cfg_payload = {
        "hepmc_path": hepmc_path,
        "pdg_id": int(pid),
        "pos_ip": ("ip" in (pos_is_ip or [])),
    }

    return (
        df.to_json(date_format="iso", orient="split"),
        events.to_json(date_format="iso", orient="split"),
        json.dumps(cfg_payload),
        "\n".join(info),
    )


def _metric_card(title: str, value: Any, subtitle: str = "") -> html.Div:
    return html.Div(
        className="metric",
        children=[
            html.Div(title, className="metric-title"),
            html.Div(str(value), className="metric-value"),
            html.Div(subtitle, className="metric-subtitle"),
        ],
    )


@app.callback(
    Output("region-metrics", "children"),
    Input("events-store", "data"),
    Input("cfg-store", "data"),
)
def update_metrics(events_json, cfg_json=None):
    if not events_json:
        return []
    events = pd.read_json(StringIO(events_json), orient="split")
    if events.empty:
        return []

    counts = events["region"].value_counts().to_dict()
    total = len(events)
    return [
        _metric_card("BSM events", total, "events with ≥1 BSM"),
        _metric_card("Decay in ANUBIS", counts.get("anubis", 0), "shaft/ceiling proxy"),
        _metric_card("Decay in ATLAS", counts.get("atlas", 0), "envelope"),
        _metric_card("Decay in cavern", counts.get("cavern", 0), "outside ATLAS"),
        _metric_card("Decay outside", counts.get("outside", 0), "outside cavern"),
    ]


@app.callback(
    Output("geom-graph", "figure"),
    Output("geom-3d", "figure"),
    Output("hist-pt", "figure"),
    Output("hist-eta", "figure"),
    Output("hist-met", "figure"),
    Output("hist-lifetime", "figure"),
    Output("bar-mothers", "figure"),
    Output("bar-children", "figure"),
    Input("df-store", "data"),
    Input("events-store", "data"),
    Input("cfg-store", "data"),
    Input("plane", "value"),
    Input("geom-options", "value"),
    Input("vertex-options", "value"),
    Input("event-region-filter", "value"),
    Input("lifetime-mode", "value"),
    Input("tree-options", "value"),
    Input("tree-depth", "value"),
    Input("tree-max-events", "value"),
    # filters
    Input("mother-pid", "value"),
    Input("child-pid", "value"),
    Input("E-lo", "value"), Input("E-hi", "value"),
    Input("pt-lo", "value"), Input("pt-hi", "value"),
    Input("p-lo", "value"), Input("p-hi", "value"),
    Input("px-lo", "value"), Input("px-hi", "value"),
    Input("py-lo", "value"), Input("py-hi", "value"),
    Input("pz-lo", "value"), Input("pz-hi", "value"),
    Input("eta-lo", "value"), Input("eta-hi", "value"),
    Input("phi-lo", "value"), Input("phi-hi", "value"),
    Input("theta-lo", "value"), Input("theta-hi", "value"),
    Input("met-lo", "value"), Input("met-hi", "value"),
)
def update_dashboard_figures(
    df_json, events_json, cfg_json,
    plane, geom_opts, vertex_opts, region_filter, lifetime_mode,
    tree_opts, tree_depth, tree_max_events,
    mother_pid, child_pid,
    E_lo, E_hi, pt_lo, pt_hi, p_lo, p_hi, px_lo, px_hi, py_lo, py_hi, pz_lo, pz_hi,
    eta_lo, eta_hi, phi_lo, phi_hi, theta_lo, theta_hi, met_lo, met_hi
):
    empty = _fig_style(go.Figure(), "No data loaded yet")
    if not df_json:
        return empty, empty, empty, empty, empty, empty, empty, empty

    df = pd.read_json(StringIO(df_json), orient="split")

    # Apply particle-level filters (mothers/children + kinematics)
    spec = ParticleFilterSpec(
        mother_pid=_int_or_none(mother_pid),
        child_pid=_int_or_none(child_pid),
        E=make_range(E_lo, E_hi),
        pt=make_range(pt_lo, pt_hi),
        p=make_range(p_lo, p_hi),
        px=make_range(px_lo, px_hi),
        py=make_range(py_lo, py_hi),
        pz=make_range(pz_lo, pz_hi),
        eta=make_range(eta_lo, eta_hi),
        phi=make_range(phi_lo, phi_hi),
        theta=make_range(theta_lo, theta_hi),
        met=make_range(met_lo, met_hi),
    )
    dff = apply_filters(df, spec)

    # Apply event-region filter
    if events_json:
        events = pd.read_json(StringIO(events_json), orient="split")
    else:
        events = build_events_table(df)

    allowed_events = None
    if region_filter == "anubis":
        allowed_events = set(events.loc[events["region"] == "anubis", "event"].astype(int).tolist())
    elif region_filter == "outside_atlas":
        allowed_events = set(events.loc[events["region"].isin(["cavern", "outside", "stable"]), "event"].astype(int).tolist())

    if allowed_events is not None:
        dff = dff[dff["event"].astype(int).isin(allowed_events)].copy()

    # base geometry
    plot_atlas = "atlas" in (geom_opts or [])
    plot_acc = "acc" in (geom_opts or [])
    show_an_ceiling = "an_ceiling" in (geom_opts or [])
    show_an_shaft = "an_shaft" in (geom_opts or [])

    if plane == "XY":
        geom2d = fig_factory_2d.figure_xy(plot_atlas=plot_atlas, plot_acceptance=plot_acc)
    elif plane == "XZ":
        geom2d = fig_factory_2d.figure_xz(plot_atlas=plot_atlas)
    else:
        geom2d = fig_factory_2d.figure_zy(plot_atlas=plot_atlas, plot_acceptance=plot_acc)

    # ANUBIS overlays
    if show_an_ceiling and plane == "XY":
        anubis_factory.add_simple_rpcs_xy(geom2d, ANUBIS_CEILING_RPCs)
    if show_an_shaft:
        if plane == "XZ":
            anubis_factory.add_shaft_rpcs_xz(geom2d, ANUBIS_SHAFT_RPCs)
        elif plane == "ZY":
            anubis_factory.add_shaft_rpcs_zy(geom2d, ANUBIS_SHAFT_RPCs)
        elif plane == "XY":
            anubis_factory.add_shaft_rpcs_xy(geom2d, ANUBIS_SHAFT_RPCs)

    show_prod = "prod" in (vertex_opts or [])
    show_dec = "dec" in (vertex_opts or [])

    geom2d = overlay_vertices(geom2d, dff, plane, show_prod, show_dec)

    # 3D base
    geom3d = fig_factory_3d.base_figure(show_box=True, show_atlas=plot_atlas)
    # add ANUBIS overlays in 3D (as point clouds / rings)
    if show_an_ceiling:
        anubis_factory.add_simple_rpcs_3d(geom3d, ANUBIS_CEILING_RPCs)
    if show_an_shaft:
        anubis_factory.add_shaft_rpcs_3d(geom3d, ANUBIS_SHAFT_RPCs)

    # overlay 3D vertices
    if show_prod:
        msk = np.isfinite(dff["prod_x_m"]) & np.isfinite(dff["prod_y_m"]) & np.isfinite(dff["prod_z_m"])
        if msk.any():
            geom3d.add_trace(go.Scatter3d(
                x=dff.loc[msk, "prod_x_m"], y=dff.loc[msk, "prod_y_m"], z=dff.loc[msk, "prod_z_m"],
                mode="markers", marker=dict(size=3, color="rgba(167,139,250,0.90)"),
                hoverinfo="skip", showlegend=False
            ))
    if show_dec:
        msk = np.isfinite(dff["dec_x_m"]) & np.isfinite(dff["dec_y_m"]) & np.isfinite(dff["dec_z_m"])
        if msk.any():
            geom3d.add_trace(go.Scatter3d(
                x=dff.loc[msk, "dec_x_m"], y=dff.loc[msk, "dec_y_m"], z=dff.loc[msk, "dec_z_m"],
                mode="markers", marker=dict(size=3, color="rgba(96,165,250,0.90)"),
                hoverinfo="skip", showlegend=False
            ))

    if ("tree" in (tree_opts or [])) and (allowed_events is not None) and (len(allowed_events) > 0):
        max_ev = _int_or_none(tree_max_events) or 40
        depth = _int_or_none(tree_depth)
        if depth is None:
            depth = 2
        bounds = (-18, 18, -18, 25, -30, 30)

        try:
            cfg = json.loads(cfg_json) if cfg_json else {}
        except Exception:
            cfg = {}
        hepmc_path = cfg.get("hepmc_path")
        pos_ip = bool(cfg.get("pos_ip", True))
        root_pdg = int(cfg.get("pdg_id", df["pid"].iloc[0]))

        if hepmc_path and os.path.exists(hepmc_path):
            cav_transform = CavernTransform(cavern=cav, hepmc_positions_are_ip_relative=pos_ip)
            tb_cfg = TrackBuildConfig(
                root_pdg=root_pdg,
                max_depth=max(0, depth),
                extend_m=30.0,
                position_transform=cav_transform.to_cavern_centre,
                bounds_m=bounds,
            )

            # sample events deterministically
            ev_list = sorted(list(allowed_events))[:max_ev]
            all_segs: List[Dict[str, Any]] = []
            for ev_id in ev_list:
                try:
                    ev = load_event_from_hepmc(hepmc_path, int(ev_id))
                    segs = build_event_tracks(ev, tb_cfg)
                except Exception:
                    continue
                for s in segs:
                    all_segs.append({
                        "pid": s.pid, "name": s.name, "charged": s.charged, "depth": s.depth, "is_root": s.is_root,
                        "x0": s.x0, "y0": s.y0, "z0": s.z0, "x1": s.x1, "y1": s.y1, "z1": s.z1,
                        "has_decay_vertex": s.has_decay_vertex, "color": _seg_color(s),
                    })

            # Draw on top (no labels in dashboard)
            geom2d = add_tracks_2d(geom2d, all_segs, plane=plane, show_labels=("labels" in (tree_opts or [])))
            geom3d = add_tracks_3d(geom3d, all_segs, show_labels=False)

    # kinematics plots
    pt_fig = make_hist(dff, "pt", "pT")
    eta_fig = make_hist(dff, "eta", "eta")
    met_fig = make_hist(dff, "met", "MET (simple truth)")
    lifetime_fig = make_hist(dff, lifetime_column_for_mode(lifetime_mode, unit="ns"), lifetime_label_for_mode(lifetime_mode, unit="ns"))
    mother_fig = make_relations_bar(dff, "mother_pids", "Top mothers")
    child_fig = make_relations_bar(dff, "child_pids", "Top daughters")

    return geom2d, geom3d, pt_fig, eta_fig, met_fig, lifetime_fig, mother_fig, child_fig


def _dash_safe_scalar(v):
    if pd.isna(v):
        return None
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, np.ndarray):
        if v.ndim == 0:
            return v.item()
        return v.tolist()
    return v


def _dash_safe_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    df = df.loc[:, ~df.columns.duplicated()].copy()

    df = df.replace([np.inf, -np.inf], np.nan)

    cols = list(df.columns)
    records: List[Dict[str, Any]] = []

    for row in df.itertuples(index=False, name=None):
        records.append({
            col: _dash_safe_scalar(val)
            for col, val in zip(cols, row)
        })

    return records


def _segment_charge_label(seg: Dict[str, Any]) -> str:
    if seg.get("is_root"):
        return "root/BSM"
    if seg.get("charged") is True:
        return "charged"
    if seg.get("charged") is False:
        return "neutral"
    return "charge unknown"


def _decay_tree_text(segs: List[Dict[str, Any]]) -> str:
    if not segs:
        return "Decay tree: no visible tracks for this event."

    by_parent: Dict[Optional[int], List[Dict[str, Any]]] = {}
    for s in sorted(segs, key=lambda x: (int(x.get("depth", 0)), int(x.get("node_id", 0)))):
        parent = s.get("parent_id")
        by_parent.setdefault(parent, []).append(s)

    def _line_label(s: Dict[str, Any]) -> str:
        decay = "decays" if s.get("has_decay_vertex") else "extrapolated/stable"
        copies = s.get("copy_count", 0)
        copy_txt = f", collapsed copies={copies}" if copies else ""
        return (
            f'{s.get("name", "particle")} (PDG {s.get("pid")}) '
            f'[depth={s.get("depth")}, {_segment_charge_label(s)}, {decay}{copy_txt}]'
        )

    roots = by_parent.get(None, [])
    if not roots:
        roots = [s for s in segs if s.get("is_root")]
    if not roots:
        roots = [segs[0]]

    lines = ["Decay tree:"]

    def render(node: Dict[str, Any], prefix: str, is_last: bool):
        connector = "└─ " if is_last else "├─ "
        lines.append(prefix + connector + _line_label(node))
        children = by_parent.get(node.get("node_id"), [])
        next_prefix = prefix + ("   " if is_last else "│  ")
        for i, child in enumerate(children):
            render(child, next_prefix, i == len(children) - 1)

    for i, root in enumerate(roots):
        render(root, "", i == len(roots) - 1)

    return "\n".join(lines)


@app.callback(
    Output("events-table", "data"),
    Output("events-table", "page_current"),
    Output("events-table", "selected_row_ids"),
    Output("event-help", "children"),
    Input("events-store", "data"),
    Input("cfg-store", "data"),
    Input("event-region-filter", "value"),
    Input("lifetime-mode", "value"),
    Input("event-number-filter", "value"),
)
def update_event_table(events_json, cfg_json, region_filter: str, lifetime_mode: str, event_filter: str):
    if not events_json:
        return [], 0, [], "Run extraction to populate the event list."

    events = pd.read_json(StringIO(events_json), orient="split")
    if events.empty:
        return [], 0, [], "No BSM events found."

    if region_filter == "anubis":
        events = events[events["region"] == "anubis"]
    elif region_filter == "outside_atlas":
        events = events[events["region"].isin(["cavern", "outside", "stable"])]

    event_filter = str(event_filter or "").strip()
    if event_filter:
        event_as_text = pd.to_numeric(events["event"], errors="coerce").astype("Int64").astype(str)
        region_as_text = events.get("region", pd.Series("", index=events.index)).astype(str)
        q = event_filter.lower()
        events = events[
            event_as_text.str.contains(q, regex=False, na=False)
            | region_as_text.str.lower().str.contains(q, regex=False, na=False)
        ]

    out = events.copy()

    if "event" in out.columns:
        out["event"] = pd.to_numeric(out["event"], errors="coerce").astype("Int64")
        out["id"] = out["event"].astype(str)
    if "n_bsm" in out.columns:
        out["n_bsm"] = pd.to_numeric(out["n_bsm"], errors="coerce").astype("Int64")
    if "region" in out.columns:
        out["region"] = out["region"].astype(str)

    evt_lt_col = event_lifetime_column_for_mode(lifetime_mode, unit="ns")
    out["hnl_lifetime_ns"] = pd.to_numeric(out.get(evt_lt_col, np.nan), errors="coerce")

    for col in ["hnl_lifetime_ns", "met", "pt_max", "E_max"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").round(3)

    help_txt = (
        f"{len(out)} events shown (region filter: {region_filter}, lifetime mode: {lifetime_mode}). "
        "Use the quick event filter for simple numbers; the column filters still support Dash syntax."
    )
    return _dash_safe_records(out), 0, [], help_txt

@app.callback(
    Output("tracks-store", "data"),
    Output("event-summary", "children"),
    Output("event-decay-tree", "children"),
    Input("events-table", "selected_row_ids"),
    Input("events-table", "selected_rows"),
    Input("apply-event-tracks", "n_clicks"),
    Input("event-depth", "n_submit"),
    Input("event-extend", "n_submit"),
    State("events-table", "data"),
    State("cfg-store", "data"),
    State("event-depth", "value"),
    State("event-extend", "value"),
)
def compute_event_tracks(selected_row_ids, selected_rows, _apply_clicks, _depth_submit, _extend_submit, table_data, cfg_json, depth, extend_m):
    if not table_data or not cfg_json:
        return None, "No event selected.", ""

    event_id: Optional[int] = None
    if selected_row_ids:
        try:
            event_id = int(str(selected_row_ids[0]))
        except Exception:
            event_id = None

    if event_id is None and selected_rows:
        try:
            event_id = int(table_data[selected_rows[0]]["event"])
        except Exception:
            event_id = None

    if event_id is None:
        return None, "Select an event in the table.", ""

    try:
        cfg = json.loads(cfg_json)
    except Exception:
        return None, "Invalid config store.", ""

    hepmc_path = cfg.get("hepmc_path")
    pdg_id = int(cfg.get("pdg_id"))
    pos_ip = bool(cfg.get("pos_ip"))

    if not hepmc_path or not os.path.exists(hepmc_path):
        return None, "HepMC path missing or not found.", ""

    row = next((r for r in table_data if str(r.get("event")) == str(event_id)), None)
    if row is None:
        return None, f"Event {event_id} is not visible in the current table filter.", ""

    cav_transform = CavernTransform(cavern=cav, hepmc_positions_are_ip_relative=pos_ip)

    try:
        event = load_event_from_hepmc(hepmc_path, event_id)
    except Exception as e:
        return None, f"Failed to load event {event_id}: {e}", ""

    depth_i = _int_or_none(depth)
    if depth_i is None:
        depth_i = 2
    extend_f = _float_or_none(extend_m)
    if extend_f is None:
        extend_f = 30.0

    tb_cfg = TrackBuildConfig(
        root_pdg=pdg_id,
        max_depth=max(0, depth_i),
        extend_m=float(extend_f),
        position_transform=cav_transform.to_cavern_centre,
        bounds_m=(-60, 60, -30, 120, -120, 120),
    )

    segs = build_event_tracks(event, tb_cfg)

    # serialize
    ser = []
    for s in segs:
        ser.append({
            "pid": s.pid,
            "name": s.name,
            "charged": s.charged,
            "depth": s.depth,
            "is_root": s.is_root,
            "x0": s.x0, "y0": s.y0, "z0": s.z0,
            "x1": s.x1, "y1": s.y1, "z1": s.z1,
            "has_decay_vertex": s.has_decay_vertex,
            "node_id": getattr(s, "node_id", None),
            "parent_id": getattr(s, "parent_id", None),
            "copy_count": getattr(s, "copy_count", 0),
            "color": _seg_color(s),
        })

    n_root = sum(1 for s in ser if s["is_root"])
    n_all = len(ser)
    n_ch = sum(1 for s in ser if (s["charged"] is True) and (not s["is_root"]))
    n_neu = sum(1 for s in ser if (s["charged"] is False) and (not s["is_root"]))

    summary = "\n".join([
        f"Event {event_id} | region={row.get('region')} | n_bsm={row.get('n_bsm')}",
        f"Tracks: total={n_all} (roots={n_root}, charged={n_ch}, neutral={n_neu})",
        f"Legend: root(BSM)=pink • charged=green • neutral=slate",
        f"HNL lifetime={row.get('hnl_lifetime_ns')} ns | MET={row.get('met')} | pTmax={row.get('pt_max')} | Emax={row.get('E_max')}",
    ])

    return json.dumps({"event": event_id, "segments": ser}), summary, _decay_tree_text(ser)


@app.callback(
    Output("event-geom-2d", "figure"),
    Output("event-geom-3d", "figure"),
    Input("tracks-store", "data"),
    Input("plane", "value"),
    Input("geom-options", "value"),
    Input("event-track-options", "value"),
)
def update_event_figures(tracks_json, plane: str, geom_opts, track_opts):
    empty2d = _fig_style(go.Figure(), "Select an event to display tracks")
    empty3d = fig_factory_3d.base_figure(show_box=True, show_atlas=True)
    empty3d.update_layout(title="Select an event to display tracks")

    if not tracks_json:
        return empty2d, empty3d

    try:
        payload = json.loads(tracks_json)
        segs = payload.get("segments", [])
    except Exception:
        return empty2d, empty3d

    show_labels = "labels" in (track_opts or [])
    charged_only = "charged_only" in (track_opts or [])

    if charged_only:
        segs = [s for s in segs if (s.get("is_root") or s.get("charged") is True)]

    plot_atlas = "atlas" in (geom_opts or [])
    plot_acc = "acc" in (geom_opts or [])
    show_an_ceiling = "an_ceiling" in (geom_opts or [])
    show_an_shaft = "an_shaft" in (geom_opts or [])

    # 2D base
    if plane == "XY":
        fig2d = fig_factory_2d.figure_xy(plot_atlas=plot_atlas, plot_acceptance=plot_acc)
    elif plane == "XZ":
        fig2d = fig_factory_2d.figure_xz(plot_atlas=plot_atlas)
    else:
        fig2d = fig_factory_2d.figure_zy(plot_atlas=plot_atlas, plot_acceptance=plot_acc)

    # ANUBIS overlays
    if show_an_ceiling and plane == "XY":
        anubis_factory.add_simple_rpcs_xy(fig2d, ANUBIS_CEILING_RPCs)
    if show_an_shaft:
        if plane == "XZ":
            anubis_factory.add_shaft_rpcs_xz(fig2d, ANUBIS_SHAFT_RPCs)
        elif plane == "ZY":
            anubis_factory.add_shaft_rpcs_zy(fig2d, ANUBIS_SHAFT_RPCs)
        elif plane == "XY":
            anubis_factory.add_shaft_rpcs_xy(fig2d, ANUBIS_SHAFT_RPCs)

    fig2d = add_tracks_2d(fig2d, segs, plane=plane, show_labels=show_labels)

    try:
        if segs:
            if plane == "XY":
                xs = [float(s["x0"]) for s in segs] + [float(s["x1"]) for s in segs]
                ys = [float(s["y0"]) for s in segs] + [float(s["y1"]) for s in segs]
            elif plane == "XZ":
                xs = [float(s["x0"]) for s in segs] + [float(s["x1"]) for s in segs]
                ys = [float(s["z0"]) for s in segs] + [float(s["z1"]) for s in segs]
            else:  # ZY
                xs = [float(s["z0"]) for s in segs] + [float(s["z1"]) for s in segs]
                ys = [float(s["y0"]) for s in segs] + [float(s["y1"]) for s in segs]

            xs = [v for v in xs if np.isfinite(v)]
            ys = [v for v in ys if np.isfinite(v)]
            if xs and ys:
                xmin, xmax = min(xs), max(xs)
                ymin, ymax = min(ys), max(ys)
                dx = max(1e-6, xmax - xmin)
                dy = max(1e-6, ymax - ymin)
                pad_x = 0.06 * dx
                pad_y = 0.06 * dy

                try:
                    xr0 = fig2d.layout.xaxis.range
                    yr0 = fig2d.layout.yaxis.range
                    if xr0:
                        xmin = min(xmin, float(xr0[0]))
                        xmax = max(xmax, float(xr0[1]))
                    if yr0:
                        ymin = min(ymin, float(yr0[0]))
                        ymax = max(ymax, float(yr0[1]))
                except Exception:
                    pass

                fig2d.update_xaxes(range=[xmin - pad_x, xmax + pad_x])
                fig2d.update_yaxes(range=[ymin - pad_y, ymax + pad_y])
    except Exception:
        pass

    # 3D base + overlays
    fig3d = fig_factory_3d.base_figure(show_box=True, show_atlas=plot_atlas)
    if show_an_ceiling:
        anubis_factory.add_simple_rpcs_3d(fig3d, ANUBIS_CEILING_RPCs)
    if show_an_shaft:
        anubis_factory.add_shaft_rpcs_3d(fig3d, ANUBIS_SHAFT_RPCs)
    fig3d = add_tracks_3d(fig3d, segs, show_labels=show_labels)

    fig2d.update_layout(title=f"Event display (2D • {plane})")
    fig3d.update_layout(title="Event display (3D)")

    return fig2d, fig3d


if __name__ == "__main__":
    app.run(debug=True)
