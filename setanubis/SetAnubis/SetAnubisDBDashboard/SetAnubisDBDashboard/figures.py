from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

px.defaults.template = "plotly_dark"
px.defaults.color_discrete_sequence = px.colors.qualitative.Set2


def fig_style(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=12, r=12, t=46, b=12),
        font=dict(color="rgba(229,231,235,0.92)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.12)", zerolinecolor="rgba(148,163,184,0.18)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.12)", zerolinecolor="rgba(148,163,184,0.18)")
    return fig


def empty(title: str, note: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=note, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font=dict(size=16))
    return fig_style(fig, title)


def dataframe(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def events_by_model(models: List[Dict[str, Any]]) -> go.Figure:
    df = dataframe(models)
    if df.empty or "model" not in df:
        return empty("Events by model")
    fig = px.bar(df, x="model", y="n_events", hover_data=[c for c in ["n_bundles", "stored_bundle_size_bytes"] if c in df])
    fig.update_xaxes(tickangle=25)
    return fig_style(fig, "Events by model")


def import_timeline(events: List[Dict[str, Any]]) -> go.Figure:
    df = dataframe(events)
    if df.empty or "date_added" not in df:
        return empty("Import timeline")
    df["date"] = pd.to_datetime(df["date_added"], errors="coerce").dt.date
    agg = df.dropna(subset=["date"]).groupby("date").size().reset_index(name="events")
    if agg.empty:
        return empty("Import timeline")
    fig = px.bar(agg, x="date", y="events")
    return fig_style(fig, "Import timeline")


def storage_breakdown(storage: Dict[str, Any]) -> go.Figure:
    labels = ["Source HEPMC", "Original runs", "Stored bundles", "CAS total"]
    values = [
        storage.get("source_hepmc_size_bytes") or storage.get("source_hepmc_size_bytes_filtered") or 0,
        storage.get("original_runs_total_size_bytes") or storage.get("original_runs_total_size_bytes_filtered") or 0,
        storage.get("stored_bundle_size_bytes") or storage.get("stored_bundle_size_bytes_filtered") or 0,
        storage.get("cas_size_bytes") or 0,
    ]
    df = pd.DataFrame({"kind": labels, "bytes": values})
    if not df["bytes"].sum():
        return empty("Storage breakdown", "No storage metrics yet. Run storage-refresh from an Events root.")
    fig = px.bar(df, x="kind", y="bytes", text="bytes", log_y=max(values) / max(min([v for v in values if v > 0] or [1]), 1) > 500)
    fig.update_traces(texttemplate="%{y:.3s} B", textposition="outside")
    return fig_style(fig, "Storage breakdown")


def per_event_storage(events: List[Dict[str, Any]]) -> go.Figure:
    df = dataframe(events)
    if df.empty:
        return empty("Per-event storage")
    for col in ["original_runs_total_size_bytes", "source_hepmc_size_bytes", "stored_bundle_size_bytes"]:
        if col not in df:
            df[col] = 0
    if not df[["original_runs_total_size_bytes", "stored_bundle_size_bytes"]].sum().sum():
        return empty("Per-event storage", "No per-event size metrics yet")
    df["ratio_bundle_original"] = df.apply(lambda r: (r["stored_bundle_size_bytes"] / r["original_runs_total_size_bytes"]) if r.get("original_runs_total_size_bytes") else None, axis=1)
    fig = px.scatter(
        df,
        x="original_runs_total_size_bytes",
        y="stored_bundle_size_bytes",
        color="model" if "model" in df else None,
        hover_name="run_name" if "run_name" in df else None,
        hover_data=[c for c in ["source_hepmc_size_bytes", "ratio_bundle_original", "sample_bundle_format", "llp_pid"] if c in df],
    )
    fig.update_traces(marker=dict(size=10, opacity=0.82))
    return fig_style(fig, "Per-event original size vs stored bundle")


def storage_ratio_hist(events: List[Dict[str, Any]]) -> go.Figure:
    df = dataframe(events)
    if df.empty or "bundle_over_original_runs" not in df:
        return empty("Bundle / original ratio")
    df = df.dropna(subset=["bundle_over_original_runs"])
    if df.empty:
        return empty("Bundle / original ratio")
    fig = px.histogram(df, x="bundle_over_original_runs", nbins=30)
    fig.update_xaxes(tickformat=".1%")
    return fig_style(fig, "Bundle / original ratio")


def artifact_sizes(artifacts: List[Dict[str, Any]]) -> go.Figure:
    df = dataframe(artifacts)
    if df.empty:
        return empty("Artifacts by kind")
    fig = px.bar(df, x="kind", y="size_bytes", text="count", hover_data=["count"])
    fig.update_traces(texttemplate="n=%{text}", textposition="outside")
    return fig_style(fig, "Artifacts by kind")


def bundle_frames(frames: Dict[str, Dict[str, Any]]) -> go.Figure:
    rows = []
    for name, info in (frames or {}).items():
        item = {"frame": name}
        item.update(info or {})
        rows.append(item)
    df = dataframe(rows)
    if df.empty:
        return empty("Bundle frames")
    fig = px.bar(df.sort_values("rows", ascending=False), x="frame", y="rows", hover_data=[c for c in ["events", "memory_bytes"] if c in df])
    fig.update_xaxes(tickangle=25)
    return fig_style(fig, "Rows by stored DataFrame")


def cross_section_hist(events: List[Dict[str, Any]]) -> go.Figure:
    df = dataframe(events)
    if df.empty or "cross_section_pb" not in df:
        return empty("Cross-section")
    df = df.dropna(subset=["cross_section_pb"])
    if df.empty:
        return empty("Cross-section")
    fig = px.histogram(df, x="cross_section_pb", nbins=40, color="model" if "model" in df else None)
    fig.update_xaxes(type="log" if (df["cross_section_pb"] > 0).all() and df["cross_section_pb"].max() / max(df["cross_section_pb"].min(), 1e-300) > 100 else None)
    return fig_style(fig, "Cross-section [pb]")


def scan_scatter(events: List[Dict[str, Any]]) -> go.Figure:
    rows = []
    for e in events:
        params = e.get("scan_params") or {}
        if not isinstance(params, dict):
            continue
        row = {"run_name": e.get("run_name"), "model": e.get("model"), "cross_section_pb": e.get("cross_section_pb")}
        row.update({k: v for k, v in params.items() if isinstance(v, (int, float))})
        rows.append(row)
    df = dataframe(rows)
    if df.empty:
        return empty("Scan overview", "No numeric scan params")
    numeric = [c for c in df.columns if c not in {"run_name", "model", "cross_section_pb"} and pd.api.types.is_numeric_dtype(df[c])]
    if not numeric:
        return empty("Scan overview", "No numeric scan params")
    x = numeric[0]
    y = "cross_section_pb" if "cross_section_pb" in df and df["cross_section_pb"].notna().any() else (numeric[1] if len(numeric) > 1 else numeric[0])
    fig = px.scatter(df, x=x, y=y, color="model" if "model" in df else None, hover_name="run_name")
    return fig_style(fig, f"Scan: {x} vs {y}")


def particle_masses(particles: List[Dict[str, Any]]) -> go.Figure:
    df = dataframe(particles)
    if df.empty or "mass" not in df:
        return empty("Particle masses")
    df = df.dropna(subset=["mass"])
    if df.empty:
        return empty("Particle masses")
    df["label"] = df.apply(lambda r: f"{r.get('name') or ''} ({int(r.get('pdg'))})", axis=1)
    fig = px.bar(df.sort_values("mass", ascending=False).head(30), x="label", y="mass", hover_data=[c for c in ["model", "width", "charge", "spin"] if c in df])
    fig.update_xaxes(tickangle=35)
    return fig_style(fig, "Particle masses")


def particle_widths(particles: List[Dict[str, Any]]) -> go.Figure:
    df = dataframe(particles)
    if df.empty or "width" not in df:
        return empty("Particle widths")
    df = df.dropna(subset=["width"])
    if df.empty:
        return empty("Particle widths")
    df["label"] = df.apply(lambda r: f"{r.get('name') or ''} ({int(r.get('pdg'))})", axis=1)
    fig = px.bar(df.sort_values("width", ascending=False).head(30), x="label", y="width", hover_data=[c for c in ["model", "mass", "charge", "spin"] if c in df])
    fig.update_xaxes(tickangle=35)
    fig.update_yaxes(type="log" if (df["width"] > 0).any() else None)
    return fig_style(fig, "Particle widths")


def model_storage(models: List[Dict[str, Any]]) -> go.Figure:
    df = dataframe(models)
    if df.empty:
        return empty("Storage by model")
    cols = [c for c in ["source_hepmc_size_bytes", "original_runs_total_size_bytes", "stored_bundle_size_bytes"] if c in df]
    if not cols:
        return empty("Storage by model")
    melted = df.melt(id_vars=["model"], value_vars=cols, var_name="kind", value_name="bytes")
    fig = px.bar(melted, x="model", y="bytes", color="kind", barmode="group")
    fig.update_xaxes(tickangle=25)
    return fig_style(fig, "Storage by model")
