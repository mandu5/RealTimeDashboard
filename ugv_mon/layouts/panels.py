"""
Status Panel Components for UGV-MON Dashboard.

패널 빌더 함수들:
- 운용 상태 (모드, 권한, 주행상태)
- 비상정지 인디케이터
- 장치 연결 상태
- 차트 패널
- 가용성 타임라인
- 로그 테이블
"""

from dash import dcc, html
import dash_mantine_components as dmc
from typing import Dict, List

from ..styles import (
    COLORS, PANEL_HEADER, PANEL_TITLE, CARD_MARGIN, FLEX_COLUMN,
    indicator_bar, status_box_style, led_style, flex_row,
)
from .charts import create_communication_chart, create_availability_timeline


# =============================================================================
# 운용 상태 패널
# =============================================================================

def create_operational_status_panel(data: Dict) -> dmc.Card:
    """현재 운용 상태 패널."""
    return dmc.Card(
        children=[
            _panel_header("현재 운용 상태"),
            html.Div(
                id="operational-status",
                children=create_operational_status_boxes(data),
                style={"display": "flex", "flexDirection": "column", "gap": "16px"},
            ),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


def create_operational_status_boxes(data: Dict) -> List:
    """운용 상태 3개 박스 생성."""
    configs = [
        ("운용모드", data.get("operationalMode", "---"), "#059669", "#064e3b", COLORS["bg_success"], "#a7f3d0"),
        ("운용권한", data.get("operationalAuthority", "---"), "#2563eb", "#1e3a8a", COLORS["bg_info"], "#bfdbfe"),
        ("주행상태", data.get("drivingState", "---"), "#475569", "#0f172a", COLORS["bg_neutral"], "#e2e8f0"),
    ]
    return [_status_box(label, value, label_color, value_color, bg, border) 
            for label, value, label_color, value_color, bg, border in configs]


def _status_box(label: str, value: str, label_color: str, value_color: str, bg: str, border: str) -> html.Div:
    """상태 박스 컴포넌트."""
    return html.Div(
        children=[
            html.Div(label, style={"fontSize": "12px", "fontWeight": "500", "color": label_color, "marginBottom": "8px"}),
            html.Div(value, style={"fontSize": "16px", "fontWeight": "700", "color": value_color}),
        ],
        style=status_box_style(bg, border),
    )


# =============================================================================
# 비상정지 패널
# =============================================================================

def create_emergency_status_panel(emergency_status: Dict[str, bool]) -> dmc.Card:
    """비상정지/이상 원인 패널."""
    return dmc.Card(
        children=[
            _panel_header("비상정지/이상 원인", COLORS["warning"]),
            html.Div(
                id="emergency-status",
                children=create_emergency_indicators(emergency_status),
                style={"display": "flex", "flexDirection": "column", "gap": "6px"},
            ),
        ],
        withBorder=True, p="lg", radius="md",
    )


def create_emergency_indicators(emergency_status: Dict[str, bool]) -> List:
    """비상정지 인디케이터 리스트."""
    return [_emergency_indicator(name, is_active) for name, is_active in emergency_status.items()]


def _emergency_indicator(name: str, is_active: bool) -> html.Div:
    """단일 비상정지 인디케이터."""
    return html.Div(
        children=[
            html.Div(style=led_style(is_active)),
            html.Span(name, style={
                "fontSize": "12px",
                "fontWeight": "600" if is_active else "500",
                "color": "#dc2626" if is_active else COLORS["text_muted"],
            }),
        ],
        style={
            "display": "flex", "alignItems": "center", "gap": "12px",
            "padding": "8px 12px", "borderRadius": "8px",
            "backgroundColor": COLORS["bg_error"] if is_active else "#f8fafc",
            "border": f"1px solid {'#fecaca' if is_active else 'transparent'}",
        },
    )


# =============================================================================
# 장치 연결 패널
# =============================================================================

def create_device_panel(devices: List[Dict]) -> dmc.Card:
    """장치 연결 상태 패널."""
    from ..components.device_grid import create_device_grid
    
    connected = sum(1 for d in devices if d.get("connected", False))
    total = len(devices)
    
    return dmc.Card(
        children=[
            html.Div(
                children=[
                    _panel_header_inline("장치 연결 상태"),
                    html.Span(f"전체: {connected}/{total} 개", style={"fontSize": "12px", "color": COLORS["text_muted"]}),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px"},
            ),
            html.Div(id="device-grid-container", children=[create_device_grid(devices)]),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


# =============================================================================
# 차트 패널
# =============================================================================

def create_charts_panel(data: Dict) -> dmc.Card:
    """통신 품질 차트 패널."""
    chart_data = data.get("combinedData", [])
    latest_pps = chart_data[-1].get("pps", 0) if chart_data else 0
    latest_jitter = chart_data[-1].get("jitter", 0) if chart_data else 0
    
    return dmc.Card(
        children=[
            _chart_header(latest_pps, latest_jitter),
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


def _chart_header(pps: int, jitter: float) -> html.Div:
    """차트 헤더 (타이틀 + 범례 + 시간 버튼)."""
    return html.Div(
        children=[
            _panel_header_inline("통신 품질 차트"),
            html.Div(children=[_legend_item("PPS (좌)", COLORS["primary"]), _legend_item("지터 (우)", COLORS["purple"])], style=flex_row("16px")),
            html.Div(children=[
                dmc.Button("30s", id="time-range-30s", variant="outline", size="xs", style={"minWidth": "40px"}),
                dmc.Button("1m", id="time-range-1m", variant="filled", size="xs", style={"minWidth": "40px"}),
                dmc.Button("5m", id="time-range-5m", variant="outline", size="xs", style={"minWidth": "40px"}),
            ], style=flex_row("4px")),
        ],
        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px"},
    )


def _chart_footer(pps: int, jitter: float) -> html.Div:
    """차트 하단 현재 값 표시."""
    return html.Div(
        children=[
            html.Div(children=[
                html.Span("PPS: ", style={"fontSize": "13px", "color": COLORS["text_muted"]}),
                html.Span(id="current-pps-display", children=f"{pps:,}", style={"fontSize": "13px", "fontWeight": "600", "color": COLORS["primary_dark"], "fontFamily": "monospace"}),
            ], style=flex_row("4px")),
            html.Div(children=[
                html.Span("지터: ", style={"fontSize": "13px", "color": COLORS["text_muted"]}),
                html.Span(id="current-jitter-display", children=f"{jitter:.1f} ms", style={"fontSize": "13px", "fontWeight": "600", "color": "#7c3aed", "fontFamily": "monospace"}),
            ], style=flex_row("4px")),
        ],
        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginTop": "12px", "paddingTop": "12px", "borderTop": f"1px solid {COLORS['border_light']}"},
    )


def _legend_item(label: str, color: str) -> html.Div:
    """범례 아이템."""
    return html.Div(
        children=[
            html.Div(style={"width": "12px", "height": "12px", "backgroundColor": color, "borderRadius": "50%"}),
            html.Span(label, style={"fontSize": "12px", "color": COLORS["text_muted"]}),
        ],
        style=flex_row("6px"),
    )


# =============================================================================
# 가용성 타임라인 패널
# =============================================================================

def create_availability_panel(data: Dict) -> dmc.Card:
    """가용성 타임라인 패널."""
    return dmc.Card(
        children=[
            _panel_header("가용성 타임라인 (1시간)"),
            dcc.Graph(
                id="availability-timeline",
                figure=create_availability_timeline(data.get("availabilitySegments", [])),
                config={"displayModeBar": False, "staticPlot": False, "doubleClick": False},
            ),
        ],
        withBorder=True, p="lg", radius="md",
    )


# =============================================================================
# 로그 테이블 패널
# =============================================================================

def create_log_panel(logs: list) -> dmc.Card:
    """로그/이벤트 테이블 패널."""
    from ..components.log_table import create_log_table, create_log_table_header
    
    return dmc.Card(
        children=[
            create_log_table_header(len(logs)),
            html.Div(
                children=[create_log_table(logs)],
                style={"border": f"1px solid {COLORS['border']}", "borderRadius": "8px", "overflow": "hidden"},
            ),
        ],
        withBorder=True, p="lg", radius="md",
    )


# =============================================================================
# 공통 헬퍼
# =============================================================================

def _panel_header(title: str, color: str = None) -> html.Div:
    """패널 헤더 (인디케이터 + 타이틀)."""
    return html.Div(
        children=[
            html.Div(style=indicator_bar(color)),
            html.Div(title, style=PANEL_TITLE),
        ],
        style=PANEL_HEADER,
    )


def _panel_header_inline(title: str) -> html.Div:
    """인라인용 패널 헤더 (marginBottom 없음)."""
    return html.Div(
        children=[html.Div(style=indicator_bar()), html.Div(title, style=PANEL_TITLE)],
        style=flex_row("8px"),
    )
