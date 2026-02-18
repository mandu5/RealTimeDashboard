"""운용 상태 패널 — 운용모드 / 권한 / 주행상태."""

import dash_mantine_components as dmc
from dash import html

from ...styles import COLORS, status_box_style
from ._common import _create_content_card

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


def create_operational_status_panel(data: dict) -> dmc.Card:
    """운용 상태 패널 (운용모드 / 권한 / 주행상태 3개 박스)."""
    return _create_content_card(
        "현재 운용 상태",
        create_operational_status_boxes(data),
        "operational-status",
        content_style={"display": "flex", "flexDirection": "column", "gap": "16px"},
    )


def create_operational_status_boxes(data: dict) -> list:
    """운용 상태 3개 박스 생성."""
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
