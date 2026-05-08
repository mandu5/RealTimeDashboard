"""
패널 공통 헬퍼 — 헤더, 카드 구조, 이력 리스트 빌더.
"""

from typing import Callable, Optional

import dash_mantine_components as dmc
from dash import html

from ...styles import (
    CARD_MARGIN,
    PANEL_HEADER,
    PANEL_TITLE,
    flex_row,
    indicator_bar,
)

# 이력/전이 패널 표시 개수
HISTORY_DISPLAY_LIMIT = 5


def panel_header(title: str, color: Optional[str] = None) -> html.Div:
    """패널 헤더 (인디케이터 바 + 타이틀)."""
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


def _create_content_card(
    title: str,
    content,
    container_id: str,
    *,
    header_color: Optional[str] = None,
    card_margin: bool = True,
    content_style: Optional[dict] = None,
) -> dmc.Card:
    """패널 카드 공통 구조 (헤더 + 컨테이너)."""
    container_style = content_style or {}
    return dmc.Card(
        children=[
            panel_header(title, header_color),
            html.Div(id=container_id, children=content, style=container_style),
        ],
        withBorder=True, p="lg", radius="md", style=CARD_MARGIN if card_margin else {},
    )


def _format_iso_timestamp(iso_str: str) -> str:
    """ISO 8601 타임스탬프의 'T' 구분자를 공백으로 변환."""
    return iso_str[:19].replace("T", " ") if iso_str else ""


def _build_list_content(
    items: list,
    empty_msg: str,
    row_builder: Callable,
    limit: int = HISTORY_DISPLAY_LIMIT,
) -> list:
    """이력/전이 패널용 리스트 컨텐츠 빌드."""
    if not items:
        return [dmc.Text(empty_msg, c="dimmed", size="sm")]
    rows = [row_builder(item) for item in reversed(items[-limit:])]
    return [dmc.Stack(rows, gap="xs")]
