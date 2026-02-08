"""
Header Bar Component for UGV-MON Dashboard.

상단 헤더 바와 상태 칩들을 제공합니다.
"""


import dash_mantine_components as dmc
from dash import html

from ..components.status_chip import create_status_chip
from ..styles import COLORS, HEADER_BAR, flex_row, indicator_bar


def create_header_bar(data: dict) -> html.Div:
    """대시보드 헤더 바 생성."""
    return html.Div(
        children=[
            html.Div(
                children=[
                    # 타이틀
                    html.Div(
                        children=[
                            html.Div(style=indicator_bar()),
                            html.H1(
                                "VIC↔OCS 실시간 모니터링",
                                style={
                                    "fontSize": "20px", "fontWeight": "700",
                                    "color": COLORS["text_primary"], "margin": "0",
                                },
                            ),
                        ],
                        style=flex_row("12px"),
                    ),
                    # 상태 칩
                    html.Div(
                        id="status-chips",
                        children=create_status_chips(data),
                        style={"display": "flex", "gap": "8px", "flexWrap": "nowrap", "alignItems": "center"},
                    ),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
            ),
        ],
        style=HEADER_BAR,
    )


def create_status_chips(data: dict) -> list:
    """헤더 상태 칩들 생성.

    연결 토글, 방향 전환, 마지막 패킷 시간을 표시합니다.
    """
    is_connected = data.get("connected", False)
    current_direction = data.get("direction", "status")

    # 방향 라벨
    if current_direction == "status":
        dir_label = "상태(50000→61000)"
        dir_color = "blue"
    else:
        dir_label = "제어(61000→50000)"
        dir_color = "orange"

    return [
        # 연결상태 토글 버튼
        dmc.Button(
            children=[
                html.Span("연결상태", style={"fontSize": "12px", "opacity": "0.7", "marginRight": "4px"}),
                html.Span("연결됨" if is_connected else "연결끊김", style={"fontSize": "12px", "fontWeight": "600"}),
            ],
            id="connection-toggle-btn",
            variant="filled" if is_connected else "outline",
            color="green" if is_connected else "red",
            size="xs",
            style={"minWidth": "120px", "height": "32px", "padding": "6px 12px"},
        ),
        # 방향 전환 버튼
        dmc.Button(
            children=[
                html.Span("방향", style={"fontSize": "12px", "opacity": "0.7", "marginRight": "4px"}),
                html.Span(dir_label, style={"fontSize": "12px", "fontWeight": "600"}),
            ],
            id="direction-toggle-btn",
            variant="filled",
            color=dir_color,
            size="xs",
            style={"minWidth": "150px", "height": "32px", "padding": "6px 12px"},
        ),
        create_status_chip("마지막 패킷", data.get("lastPacketTime", "---"), "info", min_width="140px"),
    ]
