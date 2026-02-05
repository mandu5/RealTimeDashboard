"""
차트 및 가용성 패널.

통신 품질 차트와 가용성 타임라인을 표시합니다.
"""

from dash import dcc, html
import dash_mantine_components as dmc
from typing import Dict

from ...styles import COLORS, CARD_MARGIN, flex_row
from ..charts import create_communication_chart, create_availability_timeline
from ._common import panel_header, panel_header_inline


# =============================================================================
# 통신 품질 차트 패널
# =============================================================================

def create_charts_panel(data: Dict) -> dmc.Card:
    """통신 품질 차트 패널 생성.
    
    PPS와 지터를 듀얼 Y축 차트로 표시합니다.
    
    Args:
        data: combinedData, jitterP95, jitterP99 포함
        
    Returns:
        차트 카드 컴포넌트
    """
    chart_data = data.get("combinedData", [])
    latest_pps = chart_data[-1].get("pps", 0) if chart_data else 0
    latest_jitter = chart_data[-1].get("jitter", 0) if chart_data else 0
    
    return dmc.Card(
        children=[
            _chart_header(),
            dcc.Graph(
                id="comm-quality-chart",
                figure=create_communication_chart(
                    chart_data, data.get("jitterP95", 0), data.get("jitterP99", 0), 60
                ),
                config={"displayModeBar": False, "staticPlot": False, "doubleClick": False},
            ),
            _chart_footer(latest_pps, latest_jitter),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


def _chart_header() -> html.Div:
    """차트 헤더 (타이틀 + 범례 + 시간 범위 버튼)."""
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
            html.Div(
                children=[
                    dmc.Button("30s", id="time-range-30s", variant="outline", size="xs", style={"minWidth": "40px"}),
                    dmc.Button("1m", id="time-range-1m", variant="filled", size="xs", style={"minWidth": "40px"}),
                    dmc.Button("5m", id="time-range-5m", variant="outline", size="xs", style={"minWidth": "40px"}),
                ],
                style=flex_row("4px"),
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


# =============================================================================
# 가용성 타임라인 패널
# =============================================================================

def create_availability_panel(data: Dict) -> dmc.Card:
    """가용성 타임라인 패널 생성.
    
    10분/1시간 가용성과 타임라인 차트를 표시합니다.
    
    Args:
        data: availability, availabilityHourly, availabilitySegments 포함
        
    Returns:
        가용성 카드 컴포넌트
    """
    avail_10m = data.get("availability", 0)
    avail_1h = data.get("availabilityHourly", 0)
    
    return dmc.Card(
        children=[
            panel_header("가용성 타임라인"),
            dmc.Group(
                [
                    dmc.Badge(f"10분: {avail_10m:.1f}%", color="blue", variant="light", size="lg"),
                    dmc.Badge(f"1시간: {avail_1h:.1f}%", color="teal", variant="light", size="lg"),
                ],
                gap="md",
                mb="sm",
            ),
            dcc.Graph(
                id="availability-timeline",
                figure=create_availability_timeline(data.get("availabilitySegments", [])),
                config={"displayModeBar": False, "staticPlot": False, "doubleClick": False},
            ),
        ],
        withBorder=True, p="lg", radius="md",
    )
