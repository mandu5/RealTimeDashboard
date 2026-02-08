"""
UGV-MON 대시보드 패널 모듈.

모든 대시보드 패널(운용상태, 비상정지, 장치, 차트, 이력, 로그)을 정의합니다.
main_layout.py와 update_callbacks.py에서 import하여 사용합니다.
"""

from dash import dcc, html
import dash_mantine_components as dmc
from typing import Dict, List

from ..styles import (
    COLORS, CARD_MARGIN, PANEL_HEADER, PANEL_TITLE,
    indicator_bar, flex_row, status_box_style, led_style,
)
from .charts import create_communication_chart, create_availability_timeline


# =============================================================================
# 공통 헬퍼
# =============================================================================

def panel_header(title: str, color: str = None) -> html.Div:
    """패널 헤더 (인디케이터 바 + 타이틀).

    Args:
        title: 패널 제목
        color: 인디케이터 색상 (기본: primary)
    """
    return html.Div(
        children=[
            html.Div(style=indicator_bar(color)),
            html.Div(title, style=PANEL_TITLE),
        ],
        style=PANEL_HEADER,
    )


def panel_header_inline(title: str) -> html.Div:
    """인라인용 패널 헤더 (marginBottom 없음)."""
    return html.Div(
        children=[
            html.Div(style=indicator_bar()),
            html.Div(title, style=PANEL_TITLE),
        ],
        style=flex_row("8px"),
    )


def _format_iso_timestamp(iso_str: str) -> str:
    """ISO 8601 타임스탬프에서 'T' 구분자를 공백으로 변환.

    Args:
        iso_str: ISO 형식 문자열 (예: "2026-02-06T19:54:52.123456")

    Returns:
        사람이 읽기 쉬운 형식 (예: "2026-02-06 19:54:52")
    """
    return iso_str[:19].replace("T", " ") if iso_str else ""


# =============================================================================
# 1. 운용 상태 패널
# =============================================================================

def create_operational_status_panel(data: Dict) -> dmc.Card:
    """운용 상태 패널 (운용모드 / 권한 / 주행상태 3개 박스)."""
    return dmc.Card(
        children=[
            panel_header("현재 운용 상태"),
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


def _status_box(
    label: str, value: str,
    label_color: str, value_color: str, bg: str, border: str,
) -> html.Div:
    """단일 상태 박스 컴포넌트."""
    return html.Div(
        children=[
            html.Div(label, style={
                "fontSize": "12px", "fontWeight": "500",
                "color": label_color, "marginBottom": "8px",
            }),
            html.Div(value, style={
                "fontSize": "16px", "fontWeight": "700", "color": value_color,
            }),
        ],
        style=status_box_style(bg, border),
    )


# =============================================================================
# 2. 비상정지 상태 패널
# =============================================================================

def create_emergency_status_panel(emergency_status: Dict[str, bool]) -> dmc.Card:
    """비상정지 원인 패널 (LED 인디케이터)."""
    return dmc.Card(
        children=[
            panel_header("비상정지/이상 원인", COLORS["warning"]),
            html.Div(
                id="emergency-status",
                children=create_emergency_indicators(emergency_status),
                style={"display": "flex", "flexDirection": "column", "gap": "6px"},
            ),
        ],
        withBorder=True, p="lg", radius="md",
    )


def create_emergency_indicators(emergency_status: Dict[str, bool]) -> List:
    """비상정지 인디케이터 리스트 생성."""
    return [
        _emergency_indicator(name, is_active)
        for name, is_active in emergency_status.items()
    ]


def _emergency_indicator(name: str, is_active: bool) -> html.Div:
    """단일 비상정지 인디케이터 (처리완료=초록, 발생=빨강, 비활성=회색)."""
    is_complete = name == "처리완료"

    if is_complete and is_active:
        text_color = COLORS["success_dark"]
        bg_color = COLORS["bg_success"]
        border_color = "#a7f3d0"
        led_color = "#22c55e"
    elif is_active:
        text_color = "#dc2626"
        bg_color = COLORS["bg_error"]
        border_color = "#fecaca"
        led_color = None
    else:
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
# 3. 장치 연결 상태 패널
# =============================================================================

def create_device_panel(devices: List[Dict]) -> dmc.Card:
    """장치 연결 상태 패널 (10개 장치 5x2 그리드)."""
    from ..components.device_grid import create_device_grid

    connected = sum(1 for d in devices if d.get("connected", False))
    total = len(devices)

    return dmc.Card(
        children=[
            html.Div(
                children=[
                    panel_header_inline("장치 연결 상태"),
                    html.Span(
                        f"전체: {connected}/{total} 개",
                        style={"fontSize": "12px", "color": COLORS["text_muted"]},
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "16px",
                },
            ),
            html.Div(id="device-grid-container", children=[create_device_grid(devices)]),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


# =============================================================================
# 4. 통신 품질 차트 패널
# =============================================================================

def create_charts_panel(data: Dict) -> dmc.Card:
    """통신 품질 차트 패널 (PPS + 지터 듀얼 Y축)."""
    chart_data = data.get("combinedData", [])
    latest_pps = chart_data[-1].get("pps", 0) if chart_data else 0
    latest_jitter = chart_data[-1].get("jitter", 0) if chart_data else 0

    return dmc.Card(
        children=[
            _chart_header(),
            dcc.Graph(
                id="comm-quality-chart",
                figure=create_communication_chart(
                    chart_data, data.get("jitterP95", 0), 60,
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
# 5. 가용성 타임라인 패널
# =============================================================================

def create_availability_panel(data: Dict) -> dmc.Card:
    """가용성 타임라인 패널 (10분/1시간 가용성 + 타임라인 차트)."""
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


# =============================================================================
# 6. 로그 테이블 패널
# =============================================================================

def create_log_panel(logs: list) -> dmc.Card:
    """로그/이벤트 테이블 패널."""
    from ..components.log_table import create_log_table, create_log_table_header

    return dmc.Card(
        children=[
            create_log_table_header(len(logs)),
            html.Div(
                children=[create_log_table(logs)],
                style={
                    "border": f"1px solid {COLORS['border']}",
                    "borderRadius": "8px",
                    "overflow": "hidden",
                },
            ),
        ],
        withBorder=True, p="lg", radius="md",
    )


# =============================================================================
# 7. 메시지 코드별 통계 패널
# =============================================================================

MSG_CODE_NAMES = {
    0x01: "상태보고",
    0x25: "긴급상태",
    0x40: "제어응답",
    0x10: "센서",
}


def create_msg_code_stats_panel(data: Dict) -> dmc.Card:
    """메시지 코드별 통계 패널 (탭 UI)."""
    stats = data.get("msgCodeStats", {})

    tabs_list = []
    tab_panels = []

    for code, name in MSG_CODE_NAMES.items():
        code_stats = stats.get(code, {"pps": 0, "packet_loss": 0, "avg_size": 0, "count": 0})
        tabs_list.append(dmc.TabsTab(f"0x{code:02X}", value=str(code)))
        tab_panels.append(
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
            panel_header("메시지 코드별 통계"),
            html.Div(
                id="msg-code-stats-container",
                children=[
                    dmc.Tabs(
                        value="1",
                        children=[dmc.TabsList(tabs_list, grow=True), *tab_panels],
                    ),
                ],
            ),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


def _stat_box(label: str, value: str) -> dmc.Paper:
    """통계 박스 (탭 내부 사용)."""
    return dmc.Paper(
        children=[
            dmc.Text(label, size="xs", c="dimmed"),
            dmc.Text(value, size="lg", fw=600),
        ],
        p="sm", radius="md", withBorder=True,
        style={"textAlign": "center"},
    )


# =============================================================================
# 8. 연결 이력 패널
# =============================================================================

def create_connection_history_panel(data: Dict) -> dmc.Card:
    """연결 상태 변경 이력 패널."""
    return dmc.Card(
        children=[
            panel_header("연결 이력"),
            html.Div(
                id="connection-history-container",
                children=create_connection_history_content(data),
            ),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


def create_connection_history_content(data: Dict) -> List:
    """연결 이력 컨텐츠 (콜백에서도 사용)."""
    history = data.get("connectionHistory", [])

    if not history:
        return [dmc.Text("연결 이력 없음", c="dimmed", size="sm")]

    rows = []
    for item in reversed(history[-5:]):
        status = "연결" if item.get("connected") else "끊김"
        color = "green" if item.get("connected") else "red"
        duration = item.get("duration")
        duration_str = f"({duration:.0f}초)" if duration else ""
        rows.append(
            dmc.Group([
                dmc.Badge(status, color=color, size="sm"),
                dmc.Text(_format_iso_timestamp(item.get("timestamp", "")), size="xs", c="dimmed"),
                dmc.Text(duration_str, size="xs", c="dimmed"),
            ], gap="xs")
        )
    return [dmc.Stack(rows, gap="xs")]


# =============================================================================
# 9. 운용모드 전이 패널
# =============================================================================

def create_mode_transitions_panel(data: Dict) -> dmc.Card:
    """운용 모드 전이 이력 패널."""
    return dmc.Card(
        children=[
            panel_header("운용모드 전이"),
            html.Div(
                id="mode-transitions-container",
                children=create_mode_transitions_content(data),
            ),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


def create_mode_transitions_content(data: Dict) -> List:
    """운용모드 전이 컨텐츠 (콜백에서도 사용)."""
    transitions = data.get("modeTransitions", [])

    if not transitions:
        return [dmc.Text("모드 전이 없음", c="dimmed", size="sm")]

    rows = []
    for t in reversed(transitions[-5:]):
        rows.append(
            dmc.Group([
                dmc.Text(t.get("from", "?"), size="sm", fw=500),
                dmc.Text("->", size="sm", c="dimmed"),
                dmc.Text(t.get("to", "?"), size="sm", fw=500),
                dmc.Text(_format_iso_timestamp(t.get("timestamp", "")), size="xs", c="dimmed"),
            ], gap="xs")
        )
    return [dmc.Stack(rows, gap="xs")]


# =============================================================================
# 10. 비상정지 원인 통계 패널
# =============================================================================

def create_emergency_stats_panel(data: Dict) -> dmc.Card:
    """비상정지 원인별 발생 횟수 패널."""
    return dmc.Card(
        children=[
            panel_header("비상정지 원인 통계"),
            html.Div(
                id="emergency-stats-container",
                children=create_emergency_stats_content(data),
            ),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN,
    )


def create_emergency_stats_content(data: Dict) -> List:
    """비상정지 통계 컨텐츠 (콜백에서도 사용)."""
    counts = data.get("emergencyCounts", {})

    if not counts:
        return [dmc.Text("비상정지 발생 없음", c="dimmed", size="sm")]

    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    rows = []
    for reason, count in sorted_items[:5]:
        rows.append(
            dmc.Group([
                dmc.Text(reason, size="sm"),
                dmc.Badge(str(count), color="red", variant="filled", size="sm"),
            ], justify="space-between")
        )
    return [dmc.Stack(rows, gap="xs")]


# =============================================================================
# Section 8: ML 이상 탐지 패널
# =============================================================================

def create_ml_analysis_panel(data: Dict) -> dmc.Card:
    """ML 이상 탐지 분석 패널.
    
    3D 산점도, 타임라인, 기여 특성을 표시합니다.
    모델이 준비되지 않았으면 로딩 상태를 표시합니다.
    """
    from ..charts import (
        create_anomaly_3d_scatter,
        create_anomaly_timeline,
        create_feature_contribution_chart,
        create_confidence_gauge,
    )
    
    ml_data = data.get("ml", {})
    model_status = ml_data.get("model_status", "not_ready")
    
    # 모델 준비 안 됨
    if model_status == "not_ready":
        return dmc.Card(
            children=[
                panel_header("ML 이상 탐지"),
                html.Div(
                    children=[
                        dmc.Loader(size="lg", color="blue"),
                        dmc.Text("ML 모델 학습 대기 중...", size="lg", c="dimmed", style={"marginTop": "16px"}),
                        dmc.Text("데이터 수집 후 자동 시작됩니다.", size="sm", c="dimmed", style={"marginTop": "8px"}),
                    ],
                    style={"display": "flex", "flexDirection": "column", "alignItems": "center", "justifyContent": "center", "height": "300px"},
                ),
            ],
            withBorder=True, p="lg", radius="md",
        )
    
    # ML 결과 추출
    is_anomaly = ml_data.get("is_anomaly", False)
    confidence = ml_data.get("confidence", 0)
    contributing_features = ml_data.get("contributing_features", [])
    records = ml_data.get("records", [])
    score_history = ml_data.get("score_history", [])
    anomaly_scores = [r.get("anomaly_score", 0) for r in records] if records else []
    
    return dmc.Card(
        children=[
            # 헤더 + 상태 배지
            html.Div(
                children=[
                    html.Div(
                        children=[
                            html.Div(style=indicator_bar()),
                            html.Span("ML 이상 탐지", style=PANEL_TITLE),
                            dmc.Badge(
                                "이상 감지" if is_anomaly else "정상",
                                color="red" if is_anomaly else "green",
                                size="lg",
                            ),
                        ],
                        style=flex_row("12px"),
                    ),
                    dmc.Text(f"신뢰도: {confidence:.0%}", size="sm", c="dimmed"),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px"},
            ),
            
            # 3D 산점도 + 신뢰도 게이지
            html.Div(
                children=[
                    html.Div(
                        dcc.Graph(
                            id="ml-3d-scatter",
                            figure=create_anomaly_3d_scatter(records, anomaly_scores),
                            config={"displayModeBar": False},
                            style={"height": "350px"},
                        ),
                        style={"flex": "2"},
                    ),
                    html.Div(
                        dcc.Graph(
                            id="ml-confidence-gauge",
                            figure=create_confidence_gauge(confidence),
                            config={"displayModeBar": False},
                            style={"height": "180px"},
                        ),
                        style={"flex": "1"},
                    ),
                ],
                style={"display": "flex", "gap": "16px"},
            ),
            
            # 타임라인 + 기여 특성
            html.Div(
                children=[
                    html.Div(
                        dcc.Graph(
                            id="ml-anomaly-timeline",
                            figure=create_anomaly_timeline(score_history),
                            config={"displayModeBar": False},
                            style={"height": "250px"},
                        ),
                        style={"flex": "2"},
                    ),
                    html.Div(
                        dcc.Graph(
                            id="ml-feature-contribution",
                            figure=create_feature_contribution_chart(contributing_features),
                            config={"displayModeBar": False},
                            style={"height": "200px"},
                        ),
                        style={"flex": "1"},
                    ),
                ],
                style={"display": "flex", "gap": "16px", "marginTop": "16px"},
            ),
        ],
        withBorder=True, p="lg", radius="md",
    )

