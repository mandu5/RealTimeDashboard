"""
Status Chip Component for UGV-MON Dashboard.

Displays labeled status indicators used in the header bar
for connection status, interface, filter, and other metadata.
"""

from dash import html
from typing import Literal

from ..utils.helpers import get_status_color


StatusVariant = Literal["success", "warning", "destructive", "default", "info"]


def create_status_chip(
    label: str,
    value: str,
    variant: StatusVariant = "default"
) -> html.Div:
    """
    Create a status chip component.
    
    Status chips display a label-value pair with semantic color coding.
    Used in the header bar to show connection status, active filters, etc.
    
    Args:
        label: Descriptive label (e.g., "연결상태", "인터페이스")
        value: Current value (e.g., "연결됨", "lo")
        variant: Color variant - 'success', 'warning', 'destructive', 'default', 'info'
        
    Returns:
        Dash html.Div component styled as a status chip
        
    Example:
        >>> chip = create_status_chip("연결상태", "연결됨", "success")
    """
    colors = get_status_color(variant)
    
    return html.Div(
        children=[
            html.Span(
                label,
                style={
                    "fontSize": "12px",
                    "fontWeight": "500",
                    "opacity": "0.7",
                    "color": colors["text"],
                }
            ),
            html.Span(
                str(value),
                style={
                    "fontSize": "12px",
                    "fontWeight": "600",
                    "color": colors["text"],
                }
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "8px",
            "padding": "6px 12px",
            "borderRadius": "8px",
            "border": f"1px solid {colors['border']}",
            "backgroundColor": colors["bg"],
        }
    )
