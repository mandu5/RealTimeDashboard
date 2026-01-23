"""
Header Bar Component for UGV-MON Dashboard.

Provides the top header bar with:
- Dashboard title and branding
- Connection status indicators (clickable button)
- Interface selector (dropdown)
- Active filter information
"""

from dash import html
from typing import Dict
import dash_mantine_components as dmc

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
                            "flexWrap": "nowrap",
                            "alignItems": "center",
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
    
    연결상태는 클릭 가능한 버튼, 인터페이스는 드롭다운으로 제공됩니다.
    (Live 모드에서만 활성화, Mock 모드에서는 읽기 전용)
    
    Args:
        data: Dashboard state dictionary
        
    Returns:
        List of status chip components
    """
    is_connected = data.get("connected", False)
    current_interface = data.get("interface", "lo")
    
    # 연결상태 토글 버튼 (Live 모드에서만 활성화)
    connection_button = dmc.Button(
        children=[
            html.Span("연결상태", style={"fontSize": "12px", "opacity": "0.7", "marginRight": "4px"}),
            html.Span(
                "연결됨" if is_connected else "연결끊김",
                style={"fontSize": "12px", "fontWeight": "600"},
            ),
        ],
        id="connection-toggle-btn",
        variant="filled" if is_connected else "outline",
        color="green" if is_connected else "red",
        size="xs",
        style={
            "minWidth": "120px",
            "height": "32px",
            "padding": "6px 12px",
        },
    )
    
    # 인터페이스 드롭다운 (Live 모드에서만 활성화)
    interface_select = dmc.Select(
        id="interface-select",
        value=current_interface,
        data=[
            {"value": "lo", "label": "lo (Local)"},
            {"value": "eno2", "label": "eno2"},
            {"value": "eno3", "label": "eno3"},
        ],
        size="xs",
        style={
            "minWidth": "120px",
        },
        searchable=False,
        clearable=False,
    )
    
    return [
        connection_button,
        interface_select,
        create_status_chip(
            "필터",
            data.get("filter", "---"),
            "default",
            min_width="100px",
        ),
        create_status_chip(
            "마지막 패킷",
            data.get("lastPacketTime", "---"),
            "info",
            min_width="140px",
        ),
    ]
