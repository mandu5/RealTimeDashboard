"""통신 품질 차트 패널."""

import dash_mantine_components as dmc
from dash import dcc, html

from ...config import config
from ...styles import CARD_MARGIN, COLORS, flex_row
from ._common import panel_header_inline


def create_charts_panel(data: dict) -> dmc.Card:
    """통신 품질 차트 패널 (PPS + 지터 듀얼 Y축)."""
    from ..layouts.charts import create_communication_chart

    chart_data = data.get("combinedData", [])
    latest_pps = chart_data[-1].get("pps", 0) if chart_data else 0
    latest_jitter = chart_data[-1].get("jitter", 0) if chart_data else 0

    return dmc.Card(
        children=[
            _chart_header(),
            dcc.Graph(
                id="comm-quality-chart",
                figure=create_communication_chart(
                    chart_data, data.get("jitterP95", 0), config.ui.chart_time_range_sec,
                ),
                config={"displayModeBar": False, "staticPlot": False, "doubleClick": False},
            ),
            _chart_footer(latest_pps, latest_jitter),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


def _chart_header() -> html.Div:
    """차트 헤더 (타이틀 + 범례)."""
    return html.Div(
        children=[
            panel_header_inline("통신 품질 차트"),
            html.Div(
                children=[
                    _legend_item("PPS (좌)", COLORS["primary"]),
                    _legend_item("지터 (우)", COLORS["purple"]),
                ],
                style=flex_row("16px"),
            ),
        ],
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "16px",
        },
    )


def _chart_footer(pps: int, jitter: float) -> html.Div:
    """차트 하단 현재 값 표시."""
    return html.Div(
        children=[
            html.Div(
                children=[
                    html.Span("PPS: ", style={"fontSize": "13px", "color": COLORS["text_muted"]}),
                    html.Span(
                        id="current-pps-display",
                        children=f"{pps:,}",
                        style={
                            "fontSize": "13px", "fontWeight": "600",
                            "color": COLORS["primary_dark"], "fontFamily": "monospace",
                        },
                    ),
                ],
                style=flex_row("4px"),
            ),
            html.Div(
                children=[
                    html.Span("지터: ", style={"fontSize": "13px", "color": COLORS["text_muted"]}),
                    html.Span(
                        id="current-jitter-display",
                        children=f"{jitter:.1f} ms",
                        style={
                            "fontSize": "13px", "fontWeight": "600",
                            "color": "#7c3aed", "fontFamily": "monospace",
                        },
                    ),
                ],
                style=flex_row("4px"),
            ),
        ],
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginTop": "12px",
            "paddingTop": "12px",
            "borderTop": f"1px solid {COLORS['border_light']}",
        },
    )


def _legend_item(label: str, color: str) -> html.Div:
    """차트 범례 아이템."""
    return html.Div(
        children=[
            html.Div(style={
                "width": "12px", "height": "12px",
                "backgroundColor": color, "borderRadius": "50%",
            }),
            html.Span(label, style={"fontSize": "12px", "color": COLORS["text_muted"]}),
        ],
        style=flex_row("6px"),
    )
