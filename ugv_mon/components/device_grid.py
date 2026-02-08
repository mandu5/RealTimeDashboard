"""
Device Grid Component for UGV-MON Dashboard.

Displays a 5x2 grid of device connectivity indicators
showing the connection status of 10 VIC subsystems.
"""


from dash import html

from ..styles import get_device_status_style


def create_device_item(device: dict) -> html.Div:
    """Create a single device indicator item."""
    connected = device.get("connected", False)
    warning = device.get("warning", False)
    name = device.get("name", "???")
    error_reason = device.get("error_reason")

    icon = "⚠" if (connected and warning) else ("✓" if connected else "✗")
    style = get_device_status_style(connected, warning)

    box_style = {
        "padding": "8px 12px", "borderRadius": "8px", "textAlign": "center",
        "width": "100%", "minHeight": "40px", "boxSizing": "border-box",
        "display": "flex", "alignItems": "center", "justifyContent": "center",
        **style,
    }

    content = html.Div([
        html.Span(icon, style={"fontSize": "14px", "marginRight": "6px"}),
        html.Span(name, style={"fontSize": "12px", "fontWeight": "600"}),
    ], style=box_style)

    tooltip = error_reason if (error_reason and (not connected or warning)) else None

    return html.Div(
        title=tooltip,
        style={"width": "100%", "minHeight": "40px", "boxSizing": "border-box"},
        children=content,
    )


def create_device_grid(devices: list[dict]) -> html.Div:
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


# =============================================================================
# 미사용 함수 삭제 (2026-01-20)
# - get_device_summary(): panels.py에서 직접 계산하므로 미사용
# =============================================================================
