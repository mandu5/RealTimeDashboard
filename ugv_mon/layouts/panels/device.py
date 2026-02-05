"""
장치 연결 상태 패널.

10개 장치의 연결 상태를 그리드로 표시합니다.
"""

from dash import html
import dash_mantine_components as dmc
from typing import Dict, List

from ...styles import COLORS, CARD_MARGIN
from ._common import panel_header_inline


def create_device_panel(devices: List[Dict]) -> dmc.Card:
    """장치 연결 상태 패널 생성.
    
    Args:
        devices: 장치 리스트 [{"name": str, "connected": bool}, ...]
        
    Returns:
        장치 연결 상태 카드 컴포넌트
    """
    from ...components.device_grid import create_device_grid
    
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
