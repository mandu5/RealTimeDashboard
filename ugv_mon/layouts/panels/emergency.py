"""
비상정지 상태 패널.

비상정지 원인과 처리 상태를 LED 인디케이터로 표시합니다.
"""

from dash import html
import dash_mantine_components as dmc
from typing import Dict, List

from ...styles import COLORS, led_style
from ._common import panel_header


def create_emergency_status_panel(emergency_status: Dict[str, bool]) -> dmc.Card:
    """비상정지 원인 패널 생성.
    
    Args:
        emergency_status: 원인명 → 활성화 여부 딕셔너리
        
    Returns:
        비상정지 상태 카드 컴포넌트
    """
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
    return [_emergency_indicator(name, is_active) for name, is_active in emergency_status.items()]


def _emergency_indicator(name: str, is_active: bool) -> html.Div:
    """단일 비상정지 인디케이터.
    
    - 처리완료: 초록색
    - 발생 원인: 빨간색
    - 비활성: 회색
    """
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
