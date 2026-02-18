"""로그/이벤트 테이블 패널."""

import dash_mantine_components as dmc
from dash import html

from ...styles import COLORS


def create_log_panel(logs: list) -> dmc.Card:
    """로그/이벤트 테이블 패널."""
    from ..components.log_table import create_log_table, create_log_table_header

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
