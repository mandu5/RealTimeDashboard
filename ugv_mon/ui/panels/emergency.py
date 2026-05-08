"""비상정지 상태 패널 + 비상정지 원인 통계 패널."""

import dash_mantine_components as dmc
from dash import html

from ...styles import COLORS, led_style
from ._common import HISTORY_DISPLAY_LIMIT, _create_content_card


def create_emergency_status_panel(emergency_status: dict[str, bool]) -> dmc.Card:
    """비상정지 원인 패널 (LED 인디케이터)."""
    return _create_content_card(
        "비상정지/이상 원인",
        create_emergency_indicators(emergency_status),
        "emergency-status",
        header_color=COLORS["warning"],
        card_margin=False,
        content_style={"display": "flex", "flexDirection": "column", "gap": "6px"},
    )


def create_emergency_indicators(emergency_status: dict[str, bool]) -> list:
    """비상정지 인디케이터 리스트 생성."""
    return [
        _emergency_indicator(name, is_active)
        for name, is_active in emergency_status.items()
    ]


def _emergency_indicator(name: str, is_active: bool) -> html.Div:
    """단일 비상정지 인디케이터 (처리완료=초록, 발생=빨강, 비활성=회색)."""
    is_complete = name == "처리완료"

    if is_complete and is_active:
        text_color, bg_color, border_color, led_color = (
            COLORS["success_dark"], COLORS["bg_success"], "#a7f3d0", "#22c55e"
        )
    elif is_active:
        text_color, bg_color, border_color, led_color = (
            "#dc2626", COLORS["bg_error"], "#fecaca", None
        )
    else:
        text_color, bg_color, border_color, led_color = (
            COLORS["text_muted"], "#f8fafc", "transparent", None
        )

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


def create_emergency_stats_panel(data: dict) -> dmc.Card:
    """비상정지 원인별 발생 횟수 패널."""
    return _create_content_card(
        "비상정지 원인 통계",
        create_emergency_stats_content(data),
        "emergency-stats-container",
    )


def create_emergency_stats_content(data: dict) -> list:
    """비상정지 통계 컨텐츠 (콜백에서도 사용)."""
    counts = data.get("emergencyCounts", {})
    if not counts:
        return [dmc.Text("비상정지 발생 없음", c="dimmed", size="sm")]

    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    rows = [
        dmc.Group(
            [
                dmc.Text(reason, size="sm"),
                dmc.Badge(str(count), color="red", variant="filled", size="sm"),
            ],
            style={"justifyContent": "space-between"},
        )
        for reason, count in sorted_items[:HISTORY_DISPLAY_LIMIT]
    ]
    return [dmc.Stack(rows, gap="xs")]
