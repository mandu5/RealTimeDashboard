"""
Device Grid Component for UGV-MON Dashboard.

Displays a 5x2 grid of device connectivity indicators
showing the connection status of 10 VIC subsystems.
"""

from dash import html
from typing import Dict, List

from ..utils.helpers import get_device_status_style


def create_device_item(device: Dict) -> html.Div:
    """
    Create a single device indicator item.
    
    Args:
        device: Dictionary with 'name', 'connected', 'warning' keys
        
    Returns:
        Styled div showing device status
    """
    connected = device.get("connected", False)
    warning = device.get("warning", False)
    name = device.get("name", "???")
    
    # Determine icon based on status
    if connected:
        icon = "⚠" if warning else "✓"
    else:
        icon = "✗"
    
    # Get appropriate styling
    style = get_device_status_style(connected, warning)
    
    return html.Div(
        children=[
            html.Span(
                icon,
                style={
                    "fontSize": "14px",
                    "marginRight": "6px",
                }
            ),
            html.Span(
                name,
                style={
                    "fontSize": "12px",
                    "fontWeight": "600",
                }
            ),
        ],
        style={
            "padding": "8px 12px",
            "borderRadius": "8px",
            "textAlign": "center",
            **style,
        }
    )


def create_device_grid(devices: List[Dict]) -> html.Div:
    """
    Create the device connectivity grid.
    
    Displays 10 devices in a 5-column grid showing their
    connection status with color-coded indicators.
    
    Device order follows ICD bit positions:
    - Row 1: VIC, RDC, ADC, FCAM, RCAM
    - Row 2: AUX, SCS, DIP, TCC, TM
    
    Args:
        devices: List of device dictionaries with:
            - name: Display name (VIC, RDC, etc.)
            - connected: Boolean connection status
            - warning: Boolean warning flag
            
    Returns:
        Dash html.Div containing the device grid
        
    Example:
        >>> devices = [
        ...     {"name": "VIC", "connected": True, "warning": False},
        ...     {"name": "RDC", "connected": True, "warning": False},
        ...     ...
        ... ]
        >>> grid = create_device_grid(devices)
    """
    device_items = [create_device_item(device) for device in devices]
    
    return html.Div(
        children=device_items,
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(5, 1fr)",
            "gap": "8px",
        }
    )


def get_device_summary(devices: List[Dict]) -> str:
    """
    Generate device summary text.
    
    Args:
        devices: List of device dictionaries
        
    Returns:
        Summary string like "전체: 9/10 개, 정상: 1s"
    """
    total = len(devices)
    connected = sum(1 for d in devices if d.get("connected", False))
    
    return f"전체: {connected}/{total} 개"
