from __future__ import annotations

from SetAnubis.branding import show_banner

import argparse
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
from SetAnubis.HepMCGUI.demo import demo_hepmc_path
from SetAnubis.HepMCGUI.selection_diagnostics import (
    SELECTION_STAGE_LABELS,
    SELECTION_STAGE_ORDER,
    run_standard_hnl_selection,
    standard_selection_description,
)


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
DEFAULT_HEPMC_PATH = str(demo_hepmc_path())


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


def merge_selection_diagnostics(events: pd.DataFrame, payload: Dict[str, Any]) -> pd.DataFrame:
    """Attach canonical cutflow decisions to the event-level explorer table."""
    if events.empty or not payload or payload.get("error"):
        return events

    trace_events = pd.DataFrame(payload.get("events") or [])
    if trace_events.empty or "eventNumber" not in trace_events.columns:
        return events
    trace_events = trace_events.rename(columns={"eventNumber": "event"})

    candidates = pd.DataFrame(payload.get("candidates") or [])
    if not candidates.empty and "eventNumber" in candidates.columns:
        failures = (
            candidates.groupby("eventNumber", sort=True)["first_failed_stage"]
            .first()
            .rename("first_failed_stage")
            .reset_index()
            .rename(columns={"eventNumber": "event"})
        )
        trace_events = trace_events.merge(failures, on="event", how="left")

    merged = events.merge(trace_events, on="event", how="left", suffixes=("", "_selection"))
    if "last_passed_stage" not in merged.columns:
        merged["last_passed_stage"] = "Unavailable"
    merged["last_passed_stage"] = merged["last_passed_stage"].fillna("Not evaluated")
    if "first_failed_stage" not in merged.columns:
        merged["first_failed_stage"] = None
    merged["first_failed_stage"] = merged["first_failed_stage"].fillna("—")
    return merged


app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    assets_folder=str(Path(__file__).with_name("assets")),
)
app.title = "SET-ANUBIS HepMC selection explorer"
server = app.server


def controls_sidebar(logo_src: str) -> html.Div:
    """Build the scientific controls for the event and selection views."""

    def range_row(label: str, lo_id: str, hi_id: str, unit: str = ""):
        suffix = f" [{unit}]" if unit else ""
        return html.Div(
            className="range-row",
            children=[
                html.Div(f"{label}{suffix}", className="label"),
                dcc.Input(id=lo_id, type="text", placeholder="minimum"),
                dcc.Input(id=hi_id, type="text", placeholder="maximum"),
            ],
        )

    selection = standard_selection_description()
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
                            html.H1("HepMC selection explorer"),
                            html.Div(
                                "Event-level diagnostics in the ATLAS cavern and ANUBIS acceptance.",
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
                    "Inspect LLP decay vertices, reproduce the standard HNL cutflow and connect each event to the stage at which it is rejected.",
                ],
            ),
            html.Div(
                className="card control-card",
                children=[
                    html.Div(className="section-kicker", children="Input sample"),
                    html.H2("HepMC event record"),
                    html.Div("Dataset", className="label"),
                    dcc.Dropdown(
                        id="source-profile",
                        options=[
                            {"label": "Packaged CPC HNL benchmark (7 events)", "value": "demo"},
                            {"label": "Local HepMC file", "value": "custom"},
                        ],
                        value="demo",
                        clearable=False,
                    ),
                    html.Div("HepMC2/HepMC3 path", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="hepmc-path", type="text", value=DEFAULT_HEPMC_PATH, style={"width": "100%"}),
                    html.Div("LLP PDG identifier", className="label", style={"marginTop": "10px"}),
                    dcc.Input(id="pdg-id", type="text", value="9900012", style={"width": "100%"}),
                    html.Div(className="inline-grid", children=[
                        html.Div(children=[html.Div("Maximum events", className="label"), dcc.Input(id="max-events", type="text", value="")]),
                        html.Div(children=[html.Div("Status code", className="label"), dcc.Input(id="status", type="text", value="")]),
                    ]),
                    dcc.Checklist(
                        id="ignore-self-decays",
                        options=[{"label": "Ignore trivial LLP self-decays", "value": "yes"}],
                        value=["yes"],
                        className="checklist",
                    ),
                    dcc.Checklist(
                        id="pos-is-ip",
                        options=[{"label": "Interpret vertices in the interaction-point frame", "value": "ip"}],
                        value=["ip"],
                        className="checklist",
                    ),
                    html.Button("Load sample and evaluate", id="run-btn", n_clicks=0, className="primary-action"),
                    html.Div(id="status-line", className="status scientific-status"),
                ],
            ),
            html.Div(
                className="card control-card",
                children=[
                    html.Div(className="section-kicker", children="Selection definition"),
                    html.H2("Standard HNL analysis"),
                    dcc.Dropdown(
                        id="selection-profile",
                        options=[
                            {"label": "CPC benchmark: full R5 selection", "value": "standard_hnl"},
                            {"label": "Generic LLP inspection only", "value": "generic"},
                        ],
                        value="standard_hnl",
                        clearable=False,
                    ),
                    html.Div(
                        className="parameter-list",
                        children=[
                            html.Div([html.Span("Geometry"), html.Strong(selection["geometry"])]),
                            html.Div([html.Span("MET threshold"), html.Strong(f'>{selection["minimum_met_gev"]:g} GeV')]),
                            html.Div([html.Span("Detector response"), html.Strong(f'{selection["minimum_stations"]} stations / {selection["minimum_intersections"]} intersections')]),
                            html.Div([html.Span("Track requirement"), html.Strong(f'≥ {selection["minimum_tracks"]} charged track')]),
                            html.Div([html.Span("Isolation"), html.Strong(f'ΔR > {selection["isolation_delta_r"]:g}')]),
                        ],
                    ),
                    html.Div("Require events to reach", className="label", style={"marginTop": "12px"}),
                    dcc.Dropdown(
                        id="selection-stage-filter",
                        options=[{"label": "All generated LLP events", "value": "all"}] + [
                            {"label": SELECTION_STAGE_LABELS[name], "value": name}
                            for name in SELECTION_STAGE_ORDER[1:]
                        ],
                        value="all",
                        clearable=False,
                    ),
                    html.Div("Display-region classification", className="label", style={"marginTop": "10px"}),
                    dcc.Dropdown(
                        id="event-region-filter",
                        options=[
                            {"label": "All display-region classes", "value": "all"},
                            {"label": "Inside the ANUBIS instrumented volume", "value": "anubis"},
                            {"label": "Outside the ATLAS detector volume", "value": "outside_atlas"},
                        ],
                        value="all",
                        clearable=False,
                    ),
                    html.Div("Lifetime observable", className="label", style={"marginTop": "10px"}),
                    dcc.RadioItems(
                        id="lifetime-mode",
                        options=[
                            {"label": "Proper decay time", "value": "proper"},
                            {"label": "Laboratory decay time", "value": "lab"},
                        ],
                        value="proper",
                        className="checklist compact-options",
                    ),
                ],
            ),
            html.Details(
                className="card control-card advanced-panel",
                children=[
                    html.Summary("Advanced particle-level filters"),
                    html.Div("Mother PDG", className="label"),
                    dcc.Input(id="mother-pid", type="text", value="", style={"width": "100%"}),
                    html.Div("Daughter PDG", className="label", style={"marginTop": "8px"}),
                    dcc.Input(id="child-pid", type="text", value="", style={"width": "100%"}),
                    range_row("Energy", "E-lo", "E-hi", "GeV"),
                    range_row("Transverse momentum", "pt-lo", "pt-hi", "GeV"),
                    range_row("Momentum", "p-lo", "p-hi", "GeV"),
                    range_row("pₓ", "px-lo", "px-hi", "GeV"),
                    range_row("pᵧ", "py-lo", "py-hi", "GeV"),
                    range_row("p_z", "pz-lo", "pz-hi", "GeV"),
                    range_row("η", "eta-lo", "eta-hi"),
                    range_row("φ", "phi-lo", "phi-hi", "rad"),
                    range_row("θ", "theta-lo", "theta-hi", "rad"),
                    range_row("MET", "met-lo", "met-hi", "GeV"),
                ],
            ),
            html.Div(
                className="card control-card",
                children=[
                    html.Div(className="section-kicker", children="Visualisation"),
                    html.H2("Geometry and topology"),
                    html.Div("Projection", className="label"),
                    dcc.Dropdown(
                        id="plane",
                        options=[
                            {"label": "Transverse plane (x–y)", "value": "XY"},
                            {"label": "Longitudinal plane (x–z)", "value": "XZ"},
                            {"label": "Cavern elevation (z–y)", "value": "ZY"},
                        ],
                        value="ZY",
                        clearable=False,
                    ),
                    dcc.Checklist(
                        id="geom-options",
                        options=[
                            {"label": "ATLAS exclusion envelope", "value": "atlas"},
                            {"label": "Geometric acceptance rays", "value": "acc"},
                            {"label": "ANUBIS ceiling stations", "value": "an_ceiling"},
                            {"label": "ANUBIS shaft stations", "value": "an_shaft"},
                        ],
                        value=["atlas", "an_ceiling", "an_shaft"],
                        className="checklist",
                    ),
                    dcc.Checklist(
                        id="vertex-options",
                        options=[
                            {"label": "Production vertices", "value": "prod"},
                            {"label": "Decay vertices", "value": "dec"},
                        ],
                        value=["dec"],
                        className="checklist compact-options",
                    ),
                    html.Hr(),
                    html.Div("Sampled decay-tree overlay", className="label"),
                    dcc.Checklist(
                        id="tree-options",
                        options=[
                            {"label": "Overlay decay-tree tracks", "value": "tree"},
                            {"label": "Particle labels", "value": "labels"},
                        ],
                        value=[],
                        className="checklist compact-options",
                    ),
                    html.Div(className="inline-grid", children=[
                        html.Div(children=[html.Div("Tree depth", className="label"), dcc.Input(id="tree-depth", type="text", value="2")]),
                        html.Div(children=[html.Div("Events sampled", className="label"), dcc.Input(id="tree-max-events", type="text", value="40")]),
                    ]),
                ],
            ),
        ],
    )

def overview_page() -> html.Div:
    return html.Div(
        className="workspace",
        children=[
            html.Section(
                className="workspace-header",
                children=[
                    html.Div(className="section-kicker", children="Selection-level overview"),
                    html.H2("From generated LLP decays to the final ANUBIS candidate sample"),
                    html.P(
                        "The dashboard applies the same ordered stages used by the CPC reproducibility benchmark. "
                        "Counts therefore describe cumulative survival, not independent geometric categories."
                    ),
                ],
            ),
            html.Div(id="region-metrics", className="metrics-row selection-metrics"),
            html.Div(
                className="analysis-grid analysis-grid--primary",
                children=[
                    graph_card_shell(
                        "Selection cutflow",
                        "cumulative LLP candidates after each ordered requirement",
                        dcc.Loading(dcc.Graph(id="cutflow-graph", style={"height": "48vh"}), type="dot"),
                    ),
                    html.Div(
                        className="card interpretation-card",
                        children=[
                            html.Div(className="card-title", children=[html.H2("Analysis configuration"), html.Span("standard HNL profile")]),
                            html.Div(id="selection-config-panel", className="configuration-panel"),
                            html.Div(
                                className="interpretation-note",
                                children=[
                                    html.Strong("Interpretation. "),
                                    "InCavern denotes a decay in the configured ANUBIS fiducial region; NotInATLAS then removes decays inside the ATLAS detector volume. Geometry and Tracker test detector intersections and reconstructable charged activity before MET and isolation are applied.",
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="card graph-card geometry-card",
                children=[
                    html.Div(className="card-title", children=[html.H2("Decay geometry"), html.Span("ATLAS cavern, detector stations and selected vertices")]),
                    dcc.Tabs(
                        id="geom-tabs",
                        value="2d",
                        className="tabbar",
                        parent_className="tabbar",
                        children=[
                            dcc.Tab(label="Projected geometry", value="2d", className="tab", selected_className="tab--selected"),
                            dcc.Tab(label="Three-dimensional context", value="3d", className="tab", selected_className="tab--selected"),
                        ],
                    ),
                    html.Div([dcc.Loading(dcc.Graph(id="geom-graph", style={"height": "62vh"}), type="dot")], id="geom-2d-wrap"),
                    html.Div([dcc.Loading(dcc.Graph(id="geom-3d", style={"height": "62vh"}), type="dot")], id="geom-3d-wrap", style={"display": "none"}),
                ],
            ),
            html.Section(
                className="workspace-header compact-header",
                children=[
                    html.Div(className="section-kicker", children="Kinematic diagnostics"),
                    html.H2("Properties of the currently selected event subset"),
                    html.P("Particle-level filters and the required cutflow stage are applied consistently to the distributions below."),
                ],
            ),
            html.Div(
                className="graph-row",
                children=[
                    graph_card_shell("LLP transverse momentum", "GeV", dcc.Loading(dcc.Graph(id="hist-pt", style={"height": "32vh"}), type="dot")),
                    graph_card_shell("LLP pseudorapidity", "dimensionless", dcc.Loading(dcc.Graph(id="hist-eta", style={"height": "32vh"}), type="dot")),
                    graph_card_shell("Event missing transverse momentum", "GeV", dcc.Loading(dcc.Graph(id="hist-met", style={"height": "32vh"}), type="dot")),
                ],
            ),
            graph_card_shell("LLP decay time", "selected proper/laboratory observable in ns", dcc.Loading(dcc.Graph(id="hist-lifetime", style={"height": "32vh"}), type="dot")),
            html.Div(
                className="graph-row-2",
                children=[
                    graph_card_shell("Parent-particle composition", "15 most frequent PDG identifiers", dcc.Loading(dcc.Graph(id="bar-mothers", style={"height": "36vh"}), type="dot")),
                    graph_card_shell("Daughter-particle composition", "15 most frequent PDG identifiers", dcc.Loading(dcc.Graph(id="bar-children", style={"height": "36vh"}), type="dot")),
                ],
            ),
        ],
    )


def graph_card_shell(title: str, subtitle: str, child) -> html.Div:
    """Return a consistently labelled scientific graph card."""
    return html.Div(
        className="card graph-card",
        children=[
            html.Div(className="card-title", children=[html.H2(title), html.Span(subtitle)]),
            child,
        ],
    )

def event_page() -> html.Div:
    return html.Div(
        className="workspace",
        children=[
            html.Section(
                className="workspace-header",
                children=[
                    html.Div(className="section-kicker", children="Event-level diagnosis"),
                    html.H2("Identify the first failed selection requirement and inspect the decay topology"),
                    html.P(
                        "Each row reports the furthest cumulative stage reached by the event. Select a row to load the full HepMC decay tree and its detector geometry."
                    ),
                ],
            ),
            html.Div(
                className="event-workspace",
                children=[
                    html.Div(
                        className="card event-table-card",
                        children=[
                            html.Div(className="card-title", children=[html.H2("Event selection trace"), html.Span("one row per generated event")]),
                            html.Div(
                                className="event-table-toolbar",
                                children=[
                                    html.Div("Search event, region or selection stage", className="label"),
                                    dcc.Input(
                                        id="event-number-filter",
                                        type="text",
                                        value="",
                                        placeholder="for example: 6, MET, Final, outside ATLAS",
                                        debounce=False,
                                        style={"width": "100%"},
                                    ),
                                ],
                            ),
                            html.Div(id="event-help", className="table-context"),
                            dash_table.DataTable(
                                id="events-table",
                                columns=[
                                    {"name": "Event", "id": "event", "type": "numeric"},
                                    {"name": "Last passed stage", "id": "last_passed_stage", "type": "text"},
                                    {"name": "First failed stage", "id": "first_failed_stage", "type": "text"},
                                    {"name": "Display-region class", "id": "region", "type": "text"},
                                    {"name": "LLP candidates", "id": "n_bsm", "type": "numeric"},
                                    {"name": "Decay time [ns]", "id": "hnl_lifetime_ns", "type": "numeric"},
                                    {"name": "MET [GeV]", "id": "met", "type": "numeric"},
                                    {"name": "max pT [GeV]", "id": "pt_max", "type": "numeric"},
                                ],
                                data=[],
                                page_action="native",
                                page_current=0,
                                page_size=10,
                                sort_action="native",
                                filter_action="native",
                                filter_options={"case": "insensitive"},
                                row_selectable="single",
                                selected_row_ids=[],
                                style_cell={"fontFamily": "ui-monospace, Menlo, Consolas, monospace", "fontSize": 12, "padding": "9px"},
                                style_table={"overflowX": "auto"},
                            ),
                            html.Div(id="event-summary", className="status event-summary", style={"marginTop": "12px"}),
                            html.Div(id="event-decay-tree", className="decay-tree"),
                        ],
                    ),
                    html.Div(
                        className="card graph-card event-display-card",
                        children=[
                            html.Div(className="card-title", children=[html.H2("Detector and decay topology"), html.Span("LLP root, charged and neutral descendants")]),
                            dcc.Tabs(
                                id="event-geom-tabs",
                                value="2d",
                                className="tabbar",
                                parent_className="tabbar",
                                children=[
                                    dcc.Tab(label="Projected event", value="2d", className="tab", selected_className="tab--selected"),
                                    dcc.Tab(label="Three-dimensional event", value="3d", className="tab", selected_className="tab--selected"),
                                ],
                            ),
                            html.Div([dcc.Loading(dcc.Graph(id="event-geom-2d", style={"height": "62vh"}), type="dot")], id="event-2d-wrap"),
                            html.Div([dcc.Loading(dcc.Graph(id="event-geom-3d", style={"height": "62vh"}), type="dot")], id="event-3d-wrap", style={"display": "none"}),
                            html.Div(className="event-display-controls", children=[
                                html.Div(children=[html.Div("Decay-tree depth", className="label"), dcc.Input(id="event-depth", type="text", value="2", debounce=True)]),
                                html.Div(children=[html.Div("Track extension [m]", className="label"), dcc.Input(id="event-extend", type="text", value="30", debounce=True)]),
                                html.Button("Rebuild event topology", id="apply-event-tracks", n_clicks=0, className="secondary-btn"),
                            ]),
                            dcc.Checklist(
                                id="event-track-options",
                                options=[
                                    {"label": "Particle labels", "value": "labels"},
                                    {"label": "Charged descendants only", "value": "charged_only"},
                                ],
                                value=["labels"],
                                className="checklist compact-options",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


app.layout = html.Div(
    className="app-shell",
    children=[
        dcc.Store(id="df-store"),
        dcc.Store(id="events-store"),
        dcc.Store(id="selection-store"),
        dcc.Store(id="cfg-store"),
        dcc.Store(id="tracks-store"),
        html.A("Skip to analysis", href="#analysis-workspace", className="skip-link"),
        html.Aside(className="sidebar", children=[controls_sidebar(app.get_asset_url("set-anubis-logo.png"))]),
        html.Main(
            id="analysis-workspace",
            className="main-panel",
            children=[
                html.Div(
                    className="main-navigation",
                    children=[
                        html.Div(children=[
                            html.Div(className="section-kicker", children="SET-ANUBIS analysis workspace"),
                            html.H1("HepMC event and selection diagnostics"),
                        ]),
                        dcc.Tabs(
                            id="page-tabs",
                            value="overview",
                            className="tabbar page-tabbar",
                            parent_className="tabbar page-tabbar",
                            children=[
                                dcc.Tab(label="Selection overview", value="overview", className="tab", selected_className="tab--selected"),
                                dcc.Tab(label="Event inspection", value="event", className="tab", selected_className="tab--selected"),
                            ],
                        ),
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


@app.callback(
    Output("hepmc-path", "value"),
    Input("source-profile", "value"),
    State("hepmc-path", "value"),
)
def select_input_sample(profile: str, current_path: str):
    """Select the packaged benchmark without inventing a local default path."""
    if profile == "demo":
        return DEFAULT_HEPMC_PATH
    if current_path == DEFAULT_HEPMC_PATH:
        return ""
    return no_update


@app.callback(
    Output("df-store", "data"),
    Output("events-store", "data"),
    Output("selection-store", "data"),
    Output("cfg-store", "data"),
    Output("status-line", "children"),
    Input("run-btn", "n_clicks"),
    State("hepmc-path", "value"),
    State("pdg-id", "value"),
    State("max-events", "value"),
    State("status", "value"),
    State("ignore-self-decays", "value"),
    State("pos-is-ip", "value"),
    State("selection-profile", "value"),
)
def run_extraction(
    n_clicks,
    hepmc_path,
    pdg_id,
    max_events,
    status,
    ignore_self_decays,
    pos_is_ip,
    selection_profile,
):
    if n_clicks is None:
        return no_update, no_update, no_update, no_update, no_update

    hepmc_path = str(hepmc_path or "").strip()
    if not hepmc_path:
        return None, None, None, None, "No HepMC input has been selected."
    if not os.path.exists(hepmc_path):
        return None, None, None, None, f"HepMC input not found: {hepmc_path}"

    pid = _int_or_none(pdg_id)
    if pid is None:
        return None, None, None, None, f"Invalid LLP PDG identifier: {pdg_id}"

    cav_transform = CavernTransform(
        cavern=cav,
        hepmc_positions_are_ip_relative=("ip" in (pos_is_ip or [])),
    )
    extractor = ParticleExtractor(source=HepMCFileSource(path=hepmc_path))
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
    except Exception as exc:
        return None, None, None, None, f"HepMC extraction failed: {exc}"

    selection_payload: Dict[str, Any] = {}
    selection_message = "Generic LLP inspection; canonical selection was not requested."
    if selection_profile == "standard_hnl":
        if int(pid) != 9900012:
            selection_payload = {
                "error": "The standard HNL profile is defined for PDG 9900012.",
                "profile": "standard_hnl_cpc",
            }
            selection_message = selection_payload["error"]
        else:
            try:
                selection_payload = run_standard_hnl_selection(hepmc_path)
                selection_message = (
                    "Canonical HNL selection completed: "
                    f"{selection_payload['cut_flow'].get('nLLP_Final', 0)} final candidate(s)."
                )
            except Exception as exc:
                selection_payload = {"error": str(exc), "profile": "standard_hnl_cpc"}
                selection_message = f"Canonical selection unavailable: {exc}"

    cfg_payload = {
        "hepmc_path": hepmc_path,
        "pdg_id": int(pid),
        "pos_ip": ("ip" in (pos_is_ip or [])),
        "selection_profile": selection_profile,
    }

    if df.empty:
        return (
            df.to_json(date_format="iso", orient="split"),
            pd.DataFrame().to_json(orient="split"),
            json.dumps(selection_payload),
            json.dumps(cfg_payload),
            "No LLP candidates were extracted from the selected event record.",
        )

    df = add_lifetime_columns(df)
    df["region"] = classify_rows_region(df)
    events = merge_selection_diagnostics(build_events_table(df), selection_payload)

    n_prod = int(np.isfinite(df["prod_x_m"]).sum())
    n_dec = int(np.isfinite(df["dec_x_m"]).sum())
    region_counts = events["region"].value_counts().to_dict()
    info = [
        f"Input: {Path(hepmc_path).name}",
        f"LLP PDG {pid}: {len(df)} candidate row(s) across {len(events)} event(s)",
        f"Finite vertices: production={n_prod}, decay={n_dec}",
        f"Display-region classes: {region_counts}",
        selection_message,
    ]
    return (
        df.to_json(date_format="iso", orient="split"),
        events.to_json(date_format="iso", orient="split"),
        json.dumps(selection_payload),
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


def _selection_cutflow_figure(payload: Dict[str, Any]) -> go.Figure:
    if not payload or payload.get("error"):
        return _fig_style(go.Figure(), "Selection cutflow unavailable")
    key_for_stage = {
        "Original": "nLLP_original",
        "LLPDecay": "nLLP_LLPdecay",
        "InCavern": "nLLP_InCavern",
        "NotInATLAS": "nLLP_NotInATLAS",
        "Geometry": "nLLP_Geometry",
        "Tracker": "nLLP_Tracker",
        "MET": "nLLP_MET",
        "IsoJets": "nLLP_IsoJet",
        "IsoCharged": "nLLP_IsoCharged",
        "IsoAll": "nLLP_IsoAll",
        "Final": "nLLP_Final",
    }
    cut_flow = payload.get("cut_flow") or {}
    stages = [stage for stage in SELECTION_STAGE_ORDER if key_for_stage[stage] in cut_flow]
    values = [cut_flow[key_for_stage[stage]] for stage in stages]
    labels = [SELECTION_STAGE_LABELS[stage] for stage in stages]
    fig = go.Figure(
        go.Bar(
            x=stages,
            y=values,
            customdata=labels,
            text=values,
            textposition="outside",
            hovertemplate="%{customdata}<br>candidates=%{y}<extra></extra>",
        )
    )
    fig.update_xaxes(tickangle=30, title="Ordered selection stage")
    fig.update_yaxes(title="Cumulative LLP candidates", rangemode="tozero")
    return _fig_style(fig, "Canonical SET-ANUBIS cutflow")


@app.callback(
    Output("region-metrics", "children"),
    Output("cutflow-graph", "figure"),
    Output("selection-config-panel", "children"),
    Input("events-store", "data"),
    Input("selection-store", "data"),
)
def update_selection_summary(events_json, selection_json):
    events = (
        pd.read_json(StringIO(events_json), orient="split")
        if events_json
        else pd.DataFrame()
    )
    try:
        selection = json.loads(selection_json) if selection_json else {}
    except Exception:
        selection = {}

    if selection and not selection.get("error"):
        cut_flow = selection.get("cut_flow") or {}
        metrics = [
            _metric_card("Generated", cut_flow.get("nLLP_original", 0), "LLP candidates"),
            _metric_card("ANUBIS fiducial", cut_flow.get("nLLP_InCavern", 0), "after decay-region requirement"),
            _metric_card("Outside ATLAS", cut_flow.get("nLLP_NotInATLAS", 0), "detector-volume veto"),
            _metric_card("Detector geometry", cut_flow.get("nLLP_Geometry", 0), "accepted trajectories"),
            _metric_card("MET", cut_flow.get("nLLP_MET", 0), "after pTmiss requirement"),
            _metric_card("Final", cut_flow.get("nLLP_Final", 0), "after isolation"),
        ]
        config = selection.get("configuration") or {}
        panel = [
            html.Div([html.Span("Model"), html.Strong(selection.get("model", "UFO_HNL"))]),
            html.Div([html.Span("LLP PDG"), html.Strong(str(selection.get("llp_pdg", 9900012)))]),
            html.Div([html.Span("Geometry"), html.Strong(config.get("geometry", "—"))]),
            html.Div([html.Span("MET"), html.Strong(f"> {config.get('minimum_met_gev', '—')} GeV")]),
            html.Div([html.Span("Stations / intersections"), html.Strong(f"{config.get('minimum_stations', '—')} / {config.get('minimum_intersections', '—')}")]),
            html.Div([html.Span("Isolation"), html.Strong(f"ΔR > {config.get('isolation_delta_r', '—')}")]),
        ]
        return metrics, _selection_cutflow_figure(selection), panel

    counts = events.get("region", pd.Series(dtype=str)).value_counts().to_dict() if not events.empty else {}
    metrics = [
        _metric_card("LLP events", len(events), "generic HepMC inspection"),
        _metric_card("Instrumented ANUBIS", counts.get("anubis", 0), "vertex classifier"),
        _metric_card("ATLAS volume", counts.get("atlas", 0), "vertex classifier"),
        _metric_card("Cavern", counts.get("cavern", 0), "outside ATLAS"),
    ]
    note = selection.get("error") if selection else "Load a sample to evaluate the cutflow."
    return metrics, _fig_style(go.Figure(), "Selection cutflow unavailable"), html.Div(note, className="warning-note")


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
    Input("selection-store", "data"),
    Input("selection-stage-filter", "value"),
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
    df_json, events_json, cfg_json, selection_json, selection_stage_filter,
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

    if selection_stage_filter and selection_stage_filter != "all" and selection_json:
        try:
            selection_payload = json.loads(selection_json)
            trace_events = pd.DataFrame(selection_payload.get("events") or [])
            passed_column = f"passed_{selection_stage_filter}"
            if not trace_events.empty and passed_column in trace_events.columns:
                stage_events = set(
                    trace_events.loc[trace_events[passed_column].astype(bool), "eventNumber"]
                    .astype(int)
                    .tolist()
                )
                allowed_events = stage_events if allowed_events is None else allowed_events & stage_events
        except Exception:
            pass

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
    Input("selection-stage-filter", "value"),
    Input("lifetime-mode", "value"),
    Input("event-number-filter", "value"),
)
def update_event_table(events_json, cfg_json, region_filter: str, selection_stage_filter: str, lifetime_mode: str, event_filter: str):
    if not events_json:
        return [], 0, [], "Run extraction to populate the event list."

    events = pd.read_json(StringIO(events_json), orient="split")
    if events.empty:
        return [], 0, [], "No BSM events found."

    if region_filter == "anubis":
        events = events[events["region"] == "anubis"]
    elif region_filter == "outside_atlas":
        events = events[events["region"].isin(["cavern", "outside", "stable"])]

    if selection_stage_filter and selection_stage_filter != "all":
        passed_column = f"passed_{selection_stage_filter}"
        if passed_column in events.columns:
            events = events[events[passed_column].fillna(False).astype(bool)]

    event_filter = str(event_filter or "").strip()
    if event_filter:
        event_as_text = pd.to_numeric(events["event"], errors="coerce").astype("Int64").astype(str)
        region_as_text = events.get("region", pd.Series("", index=events.index)).astype(str)
        last_stage = events.get("last_passed_stage", pd.Series("", index=events.index)).astype(str)
        first_failed = events.get("first_failed_stage", pd.Series("", index=events.index)).astype(str)
        q = event_filter.lower()
        events = events[
            event_as_text.str.contains(q, regex=False, na=False)
            | region_as_text.str.lower().str.contains(q, regex=False, na=False)
            | last_stage.str.lower().str.contains(q, regex=False, na=False)
            | first_failed.str.lower().str.contains(q, regex=False, na=False)
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

    stage_text = "all stages" if selection_stage_filter == "all" else f"reached {selection_stage_filter}"
    help_txt = (
        f"{len(out)} event(s) shown; {stage_text}; decay-region filter={region_filter}; "
        f"lifetime observable={lifetime_mode}. Column filters use the standard Dash syntax."
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
        f"Event {event_id} | last passed={row.get('last_passed_stage', '—')} | first failed={row.get('first_failed_stage', '—')}",
        f"Display-region class={row.get('region')} | LLP candidates={row.get('n_bsm')} | MET={row.get('met')} GeV",
        f"Topology segments: total={n_all} (LLP roots={n_root}, charged={n_ch}, neutral={n_neu})",
        f"Decay time={row.get('hnl_lifetime_ns')} ns | max pT={row.get('pt_max')} GeV",
        "Legend: LLP root=pink • charged descendant=green • neutral descendant=slate",
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


def main(argv: Optional[List[str]] = None) -> None:
    show_banner(force=True)
    """Run the selection-aware HepMC event explorer."""
    parser = argparse.ArgumentParser(
        description="Inspect HepMC LLP events and reproduce the SET-ANUBIS selection diagnostics"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
