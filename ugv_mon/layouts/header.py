"""
Header Bar Component for UGV-MON Dashboard.

Provides the top header bar with:
- Dashboard title and branding
- Connection status indicators
- Active filter information
"""

from dash import html
from typing import Dict

from ..components.status_chip import create_status_chip


def create_header_bar(data: Dict) -> html.Div:
    """
    Create the dashboard header bar.
    
    Contains:
    - Left: Title with accent bar
    - Right: Status chips (connection, interface, filter, time range)
    
    Args:
        data: Dashboard state with connection info
        
    Returns:
        Styled header div component
        
    Example:
        >>> data = {
        ...     "connected": True,
        ...     "interface": "lo",
        ...     "filter": "50000→61000",
        ... }
        >>> header = create_header_bar(data)
    """
    is_connected = data.get("connected", False)
    
    return html.Div(
        children=[
            html.Div(
                children=[
                    # Title section
                    html.Div(
                        children=[
                            # Accent bar
                            html.Div(
                                style={
                                    "width": "4px",
                                    "height": "32px",
                                    "backgroundColor": "#3b82f6",
                                    "borderRadius": "9999px",
                                }
                            ),
                            # Title text
                            html.H1(
                                "VIC↔OCS 실시간 모니터링",
                                style={
                                    "fontSize": "20px",
                                    "fontWeight": "700",
                                    "color": "#1e293b",
                                    "margin": "0",
                                }
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "12px",
                        }
                    ),
                    # Status chips
                    html.Div(
                        id="status-chips",
                        children=create_status_chips(data),
                        style={
                            "display": "flex",
                            "gap": "8px",
                        }
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                }
            ),
        ],
        style={
            "backgroundColor": "white",
            "border": "1px solid #e2e8f0",
            "borderRadius": "12px",
            "padding": "16px 24px",
            "marginBottom": "24px",
            "boxShadow": "0 1px 3px 0 rgba(0, 0, 0, 0.1)",
        }
    )


def create_status_chips(data: Dict) -> list:
    """
    Create the row of status chips for the header.
    
    Args:
        data: Dashboard state dictionary
        
    Returns:
        List of status chip components
    """
    is_connected = data.get("connected", False)
    
    return [
        create_status_chip(
            "연결상태",
            "연결됨" if is_connected else "연결끊김",
            "success" if is_connected else "destructive",
        ),
        create_status_chip(
            "인터페이스",
            data.get("interface", "---"),
            "default",
        ),
        create_status_chip(
            "필터",
            data.get("filter", "---"),
            "default",
        ),
        create_status_chip(
            "마지막 패킷",
            data.get("lastPacketTime", "---"),
            "info",
        ),
    ]
