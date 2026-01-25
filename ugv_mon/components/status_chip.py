"""
Status Chip Component for UGV-MON Dashboard.

Displays labeled status indicators used in the header bar
for connection status, interface, filter, and other metadata.
"""

from dash import html
from typing import Literal

from ..styles import get_status_color


StatusVariant = Literal["success", "warning", "destructive", "default", "info"]


def create_status_chip(
    label: str,
    value: str,
    variant: StatusVariant = "default",
    min_width: str = None
) -> html.Div:
    """
    Create a status chip component.
    
    Status chips display a label-value pair with semantic color coding.
    Used in the header bar to show connection status, active filters, etc.
    
    Args:
        label: Descriptive label (e.g., "연결상태", "인터페이스")
        value: Current value (e.g., "연결됨", "lo")
        variant: Color variant - 'success', 'warning', 'destructive', 'default', 'info'
        min_width: Minimum width to prevent layout shift (e.g., "120px")
        
    Returns:
        Dash html.Div component styled as a status chip
        
    Example:
        >>> chip = create_status_chip("연결상태", "연결됨", "success", "100px")
    """
    colors = get_status_color(variant)
    
    chip_style = {
        "display": "flex",
        "alignItems": "center",
        "gap": "8px",
        "padding": "6px 12px",
        "borderRadius": "8px",
        "border": f"1px solid {colors['border']}",
        "backgroundColor": colors["bg"],
        "flexShrink": "0",
        "width": "fit-content",
    }
    
    if min_width:
        chip_style["minWidth"] = min_width
    
    return html.Div(
        children=[
            html.Span(
                label,
                style={
                    "fontSize": "12px",
                    "fontWeight": "500",
                    "opacity": "0.7",
                    "color": colors["text"],
                    "whiteSpace": "nowrap",
                    "flexShrink": "0",
                }
            ),
            html.Span(
                str(value),
                style={
                    "fontSize": "12px",
                    "fontWeight": "600",
                    "color": colors["text"],
                    "whiteSpace": "nowrap",
                    "flexShrink": "0",
                }
            ),
        ],
        style=chip_style
    )
