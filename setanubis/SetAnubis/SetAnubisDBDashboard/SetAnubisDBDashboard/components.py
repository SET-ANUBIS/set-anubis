from typing import Any, Dict, Iterable, List, Optional

from dash import dash_table, html


def card(title: str, subtitle: str = "", children: Optional[List[Any]] = None, className: str = "card"):
    return html.Div(
        className=className,
        children=[
            html.Div(className="card-title", children=[html.H2(title), html.Span(subtitle)]),
            *(children or []),
        ],
    )


def graph_card(title: str, graph, subtitle: str = ""):
    return card(title, subtitle, [graph], className="card graph-card")


def metric(label: str, value: str, sub: str = "", tone: str = ""):
    cls = f"metric {tone}".strip()
    return html.Div(className=cls, children=[html.Div(label, className="k"), html.Div(value, className="v"), html.Div(sub, className="s")])


def metrics_row(items: Iterable[Any]):
    return html.Div(list(items), className="metrics-row")


def status_box(text: str = "", **kwargs):
    return html.Div(text, className="status", **kwargs)


def data_table(table_id: str, columns: List[Dict[str, str]], data: List[Dict[str, Any]], page_size: int = 12, row_selectable: Optional[str] = None):
    return dash_table.DataTable(
        id=table_id,
        columns=columns,
        data=data,
        page_size=page_size,
        sort_action="native",
        filter_action="native",
        row_selectable=row_selectable,
        style_cell={
            "fontFamily": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            "fontSize": 12,
            "padding": "8px",
            "maxWidth": 260,
            "overflow": "hidden",
            "textOverflow": "ellipsis",
        },
        style_table={"overflowX": "auto"},
        style_as_list_view=False,
    )
