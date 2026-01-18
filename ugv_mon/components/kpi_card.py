"""
KPI Card Component for UGV-MON Dashboard.

Displays key performance indicators in card format with
optional progress bar for percentage values.
"""

from dash import html
import dash_mantine_components as dmc
from typing import Optional


def create_kpi_card(
    title: str,
    value: str | int | float,
    unit: str = "",
    show_progress: bool = False,
    progress_value: float = 0,
    progress_color: str = "blue"
) -> dmc.Card:
    """
    Create a KPI card component.
    
    KPI cards display key metrics in a consistent card format.
    Used in the KPI row to show capture PPS, availability, jitter, etc.
    
    Args:
        title: Card title/label (e.g., "수신 pps", "가용성 (5분)")
        value: Metric value to display
        unit: Unit suffix (e.g., "pps", "%", "ms")
        show_progress: Whether to show progress bar (for percentages)
        progress_value: Progress bar fill percentage (0-100)
        progress_color: Mantine color for progress bar
        
    Returns:
        Dash Mantine Card component
        
    Example:
        >>> card = create_kpi_card("가용성 (5분)", 99.98, "%", True, 99.98, "green")
    """
    # Build value display with optional unit
    value_display = [
        html.Span(
            str(value),
            style={
                "fontSize": "24px",
                "fontWeight": "700",
                "color": "#0f172a",
            }
        ),
    ]
    
    if unit:
        value_display.append(
            html.Span(
                f" {unit}",
                style={
                    "fontSize": "12px",
                    "color": "#64748b",
                    "fontWeight": "500",
                    "marginLeft": "4px",
                }
            )
        )
    
    # Build card content
    card_content = [
        # Title
        html.Div(
            title,
            style={
                "fontSize": "11px",
                "color": "#64748b",
                "fontWeight": "500",
                "marginBottom": "8px",
            }
        ),
        # Value with unit
        html.Div(value_display),
    ]
    
    # Optional progress bar for percentage KPIs
    if show_progress:
        card_content.append(
            dmc.Progress(
                value=min(progress_value, 100),  # Clamp to 100
                color=progress_color,
                size="sm",
                style={"marginTop": "8px"},
            )
        )
    
    return dmc.Card(
        children=[html.Div(card_content)],
        withBorder=True,
        p="md",
        radius="md",
        style={"height": "100%"},
    )


def create_kpi_cards_row(data: dict) -> list:
    """
    Create all 8 KPI cards for the dashboard.
    
    Args:
        data: Dashboard state dictionary with KPI values
        
    Returns:
        List of KPI card components
    """
    return [
        create_kpi_card(
            "수신 pps",
            data.get("capturePps", 0),
            "pps",
            True,
            70,  # Relative to expected ~1000 pps
            "blue"
        ),
        create_kpi_card(
            "필터 통과율",
            data.get("filterPass", 0),
            "%",
            True,
            data.get("filterPass", 0),
            "green"
        ),
        create_kpi_card(
            "파싱 성공률",
            data.get("parseSuccess", 0),
            "%",
            True,
            data.get("parseSuccess", 0),
            "green"
        ),
        create_kpi_card(
            "체크섬 오류율",
            data.get("checksumFail", 0),
            "%",
        ),
        create_kpi_card(
            "추정 패킷 손실",
            data.get("packetLoss", 0),
            "pkts",
        ),
        create_kpi_card(
            "가용성 (5분)",
            data.get("availability5min", 0),
            "%",
            True,
            data.get("availability5min", 0),
            "green"
        ),
        create_kpi_card(
            "가용성 (1시간)",
            data.get("availability1hour", 0),
            "%",
            True,
            data.get("availability1hour", 0),
            "green"
        ),
        create_kpi_card(
            "지터 (P95/P99)",
            f"{data.get('jitterP95', 0)} / {data.get('jitterP99', 0)}",
            "ms",
        ),
    ]
