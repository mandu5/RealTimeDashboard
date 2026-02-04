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
    COLORS, PANEL_HEADER, PANEL_TITLE, CARD_MARGIN,
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
    # 상태별 스타일 설정 (styles.py COLORS 사용)
    STATUS_STYLES = {
        "mode": {
            "label_color": COLORS["success_dark"],
            "value_color": "#064e3b",
            "bg": COLORS["bg_success"],
            "border": "#a7f3d0",
        },
        "authority": {
            "label_color": COLORS["primary"],
            "value_color": COLORS["primary_dark"],
            "bg": COLORS["bg_info"],
            "border": "#bfdbfe",
        },
        "driving": {
            "label_color": COLORS["text_muted"],
            "value_color": COLORS["text_dark"],
            "bg": COLORS["bg_neutral"],
            "border": COLORS["border"],
        },
    }
    
    configs = [
        ("운용모드", data.get("operationalMode", "---"), STATUS_STYLES["mode"]),
        ("운용권한", data.get("operationalAuthority", "---"), STATUS_STYLES["authority"]),
        ("주행상태", data.get("drivingState", "---"), STATUS_STYLES["driving"]),
    ]
    
    return [_status_box(label, value, **style) for label, value, style in configs]


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
    """단일 비상정지 인디케이터.
    
    처리완료(complete)는 초록색, 발생원은 빨간색으로 표시.
    """
    # 처리완료는 초록색, 그 외 발생원은 빨간색
    is_complete = name == "처리완료"
    
    if is_complete and is_active:
        # 처리완료 활성: 초록색
        text_color = COLORS["success_dark"]
        bg_color = COLORS["bg_success"]
        border_color = "#a7f3d0"
        led_color = "#22c55e"  # 초록 LED
    elif is_active:
        # 발생원 활성: 빨간색
        text_color = "#dc2626"
        bg_color = COLORS["bg_error"]
        border_color = "#fecaca"
        led_color = None  # 기본 빨간 LED
    else:
        # 비활성: 회색
        text_color = COLORS["text_muted"]
        bg_color = "#f8fafc"
        border_color = "transparent"
        led_color = None
    
    return html.Div(
        children=[
            html.Div(style=led_style(is_active, led_color)),
            html.Span(name, style={
                "fontSize": "12px",
                "fontWeight": "600" if is_active else "500",
                "color": text_color,
            }),
        ],
        style={
            "display": "flex", "alignItems": "center", "gap": "12px",
            "padding": "8px 12px", "borderRadius": "8px",
            "backgroundColor": bg_color,
            "border": f"1px solid {border_color}",
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
# msg_code별 통계 패널 (Phase 3)
# =============================================================================

MSG_CODE_NAMES = {
    0x01: "상태보고",
    0x25: "긴급상태",
    0x40: "제어응답",
    0x10: "센서",
}


def create_msg_code_stats_panel(data: Dict) -> dmc.Card:
    """msg_code별 통계 패널."""
    stats = data.get("msgCodeStats", {})
    
    # 탭 내용 생성
    tabs_list = []
    panels = []
    
    for code, name in MSG_CODE_NAMES.items():
        code_stats = stats.get(code, {"pps": 0, "packet_loss": 0, "avg_size": 0, "count": 0})
        tabs_list.append(dmc.TabsTab(f"0x{code:02X}", value=str(code)))
        panels.append(
            dmc.TabsPanel(
                children=[
                    dmc.SimpleGrid(
                        cols=4,
                        children=[
                            _stat_box("PPS", f"{code_stats.get('pps', 0)}/s"),
                            _stat_box("패킷 손실", f"{code_stats.get('packet_loss', 0)}"),
                            _stat_box("평균 크기", f"{code_stats.get('avg_size', 0):.0f}B"),
                            _stat_box("총 패킷", f"{code_stats.get('count', 0):,}"),
                        ],
                    ),
                ],
                value=str(code),
                pt="sm",
            )
        )
    
    return dmc.Card(
        children=[
            _panel_header("메시지 코드별 통계"),
            html.Div(
                id="msg-code-stats-container",
                children=[
                    dmc.Tabs(
                        value="1",  # 기본: 0x01
                        children=[
                            dmc.TabsList(tabs_list, grow=True),
                            *panels,
                        ],
                    ),
                ],
            ),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


def _stat_box(label: str, value: str) -> dmc.Paper:
    """통계 박스."""
    return dmc.Paper(
        children=[
            dmc.Text(label, size="xs", c="dimmed"),
            dmc.Text(value, size="lg", fw=600),
        ],
        p="sm",
        radius="md",
        withBorder=True,
        style={"textAlign": "center"},
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
    """가용성 타임라인 패널 (요약 통계 포함)."""
    avail_10m = data.get("availability", 0)
    avail_1h = data.get("availabilityHourly", 0)
    
    return dmc.Card(
        children=[
            _panel_header("가용성 타임라인"),
            # 요약 통계
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

# =============================================================================
# Phase 4: 연결 이력 패널
# =============================================================================

def create_connection_history_panel(data: Dict) -> dmc.Card:
    """연결 상태 변경 이력 패널."""
    history = data.get("connectionHistory", [])
    
    if not history:
        content = dmc.Text("연결 이력 없음", c="dimmed", size="sm")
    else:
        rows = []
        for item in reversed(history[-5:]):  # 최근 5개
            status = "연결" if item.get("connected") else "끊김"
            color = "green" if item.get("connected") else "red"
            duration = item.get("duration")
            duration_str = f"({duration:.0f}초)" if duration else ""
            rows.append(
                dmc.Group([
                    dmc.Badge(status, color=color, size="sm"),
                    dmc.Text(item.get("timestamp", "")[:19], size="xs", c="dimmed"),
                    dmc.Text(duration_str, size="xs", c="dimmed"),
                ], gap="xs")
            )
        content = dmc.Stack(rows, gap="xs")
    
    return dmc.Card(
        children=[
            _panel_header("연결 이력"),
            content,
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


# =============================================================================
# Phase 5: 운용상태 전이 패널
# =============================================================================

def create_mode_transitions_panel(data: Dict) -> dmc.Card:
    """운용 모드 전이 이력 패널."""
    transitions = data.get("modeTransitions", [])
    
    if not transitions:
        content = dmc.Text("모드 전이 없음", c="dimmed", size="sm")
    else:
        rows = []
        for t in reversed(transitions[-5:]):
            rows.append(
                dmc.Group([
                    dmc.Text(t.get("from", "?"), size="sm", fw=500),
                    dmc.Text("→", size="sm", c="dimmed"),
                    dmc.Text(t.get("to", "?"), size="sm", fw=500),
                    dmc.Text(t.get("timestamp", "")[:19], size="xs", c="dimmed"),
                ], gap="xs")
            )
        content = dmc.Stack(rows, gap="xs")
    
    return dmc.Card(
        children=[
            _panel_header("운용모드 전이"),
            content,
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


# =============================================================================
# Phase 6: 비상정지 원인 통계 패널  
# =============================================================================

def create_emergency_stats_panel(data: Dict) -> dmc.Card:
    """비상정지 원인별 발생 횟수."""
    counts = data.get("emergencyCounts", {})
    
    if not counts:
        content = dmc.Text("비상정지 발생 없음", c="dimmed", size="sm")
    else:
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        rows = []
        for reason, count in sorted_items[:5]:  # 상위 5개
            rows.append(
                dmc.Group([
                    dmc.Text(reason, size="sm"),
                    dmc.Badge(str(count), color="red", variant="filled", size="sm"),
                ], justify="space-between")
            )
        content = dmc.Stack(rows, gap="xs")
    
    return dmc.Card(
        children=[
            _panel_header("비상정지 원인"),
            content,
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
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
