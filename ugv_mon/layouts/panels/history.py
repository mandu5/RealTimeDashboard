"""
이력 및 통계 패널 (Phase 4-6).

연결 이력, 운용모드 전이, 비상정지 통계를 표시합니다.
"""

from dash import html
import dash_mantine_components as dmc
from typing import Dict, List

from ...styles import CARD_MARGIN
from ._common import panel_header


# =============================================================================
# msg_code별 통계 (Phase 3)
# =============================================================================

MSG_CODE_NAMES = {
    0x01: "상태보고",
    0x25: "긴급상태",
    0x40: "제어응답",
    0x10: "센서",
}


def create_msg_code_stats_panel(data: Dict) -> dmc.Card:
    """메시지 코드별 통계 패널.
    
    각 메시지 코드별 PPS, 패킷 손실, 평균 크기, 총 패킷 수를 탭으로 표시합니다.
    """
    stats = data.get("msgCodeStats", {})
    
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
            panel_header("메시지 코드별 통계"),
            html.Div(
                id="msg-code-stats-container",
                children=[
                    dmc.Tabs(
                        value="1",
                        children=[dmc.TabsList(tabs_list, grow=True), *panels],
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
        p="sm", radius="md", withBorder=True,
        style={"textAlign": "center"},
    )


# =============================================================================
# Phase 4: 연결 이력
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
                dmc.Text(item.get("timestamp", "")[:19], size="xs", c="dimmed"),
                dmc.Text(duration_str, size="xs", c="dimmed"),
            ], gap="xs")
        )
    return [dmc.Stack(rows, gap="xs")]


# =============================================================================
# Phase 5: 운용모드 전이
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
                dmc.Text("→", size="sm", c="dimmed"),
                dmc.Text(t.get("to", "?"), size="sm", fw=500),
                dmc.Text(t.get("timestamp", "")[:19], size="xs", c="dimmed"),
            ], gap="xs")
        )
    return [dmc.Stack(rows, gap="xs")]


# =============================================================================
# Phase 6: 비상정지 원인 통계
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
