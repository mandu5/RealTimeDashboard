"""
패널 공통 헬퍼 함수.

모든 패널에서 사용하는 공통 스타일 및 헬퍼 함수 정의.
"""

from dash import html
from ...styles import PANEL_HEADER, PANEL_TITLE, indicator_bar, flex_row


def panel_header(title: str, color: str = None) -> html.Div:
    """패널 헤더 생성.
    
    인디케이터 바와 타이틀을 포함하는 표준 헤더입니다.
    
    Args:
        title: 패널 제목
        color: 인디케이터 색상 (기본: COLORS["primary"])
        
    Returns:
        헤더 Div 컴포넌트
    """
    return html.Div(
        children=[
            html.Div(style=indicator_bar(color)),
            html.Div(title, style=PANEL_TITLE),
        ],
        style=PANEL_HEADER,
    )


def panel_header_inline(title: str) -> html.Div:
    """인라인용 패널 헤더 (marginBottom 없음).
    
    다른 요소와 같은 줄에 배치할 때 사용합니다.
    """
    return html.Div(
        children=[
            html.Div(style=indicator_bar()),
            html.Div(title, style=PANEL_TITLE),
        ],
        style=flex_row("8px"),
    )
