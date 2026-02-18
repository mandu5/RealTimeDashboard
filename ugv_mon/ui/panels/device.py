"""장치 연결 상태 패널."""

import dash_mantine_components as dmc
from dash import html

from ...styles import CARD_MARGIN, COLORS
from ._common import panel_header_inline


def create_device_panel(devices: list[dict]) -> dmc.Card:
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
