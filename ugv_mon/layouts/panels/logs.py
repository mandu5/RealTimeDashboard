"""
로그 테이블 패널.

패킷 로그를 AG Grid 테이블로 표시합니다.
"""

from dash import html
import dash_mantine_components as dmc
from typing import List

from ...styles import COLORS


def create_log_panel(logs: list) -> dmc.Card:
    """로그/이벤트 테이블 패널 생성.
    
    Args:
        logs: 로그 엔트리 리스트
        
    Returns:
        로그 테이블 카드 컴포넌트
    """
    from ...components.log_table import create_log_table, create_log_table_header
    
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
