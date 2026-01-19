"""
Status Panel Components for UGV-MON Dashboard.

Provides panel builders for:
- Operational status (mode, authority, driving state)
- Emergency status indicators
- Device connectivity grid panel
"""

from dash import html
import dash_mantine_components as dmc
from typing import Dict, List


def create_operational_status_panel(data: Dict) -> dmc.Card:
    """
    Create the operational status panel.
    
    Displays three key operational indicators:
    - 운용모드 (Operation Mode): Current VIC operation mode
    - 운용권한 (Authority): Who has control authority
    - 주행상태 (Driving State): Current driving mode
    
    Args:
        data: Dashboard state with operationalMode, operationalAuthority, drivingState
        
    Returns:
        Mantine Card component
    """
    return dmc.Card(
        children=[
            # Panel header
            html.Div(
                children=[
                    html.Div(
                        style={
                            "width": "4px",
                            "height": "16px",
                            "backgroundColor": "#3b82f6",
                            "borderRadius": "9999px",
                        }
                    ),
                    html.Div(
                        "현재 운용 상태",
                        style={
                            "fontSize": "14px",
                            "fontWeight": "600",
                            "color": "#334155",
                        }
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                    "marginBottom": "16px",
                }
            ),
            # Status boxes
            html.Div(
                id="operational-status",
                children=create_operational_status_boxes(data),
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "16px",
                }
            ),
        ],
        withBorder=True,
        p="lg",
        radius="md",
        style={"marginBottom": "24px"},
    )


def create_operational_status_boxes(data: Dict) -> List:
    """
    Create the three operational status indicator boxes.
    
    Args:
        data: Dashboard state dictionary
        
    Returns:
        List of styled div components
    """
    return [
        # Operation Mode (Green)
        html.Div(
            children=[
                html.Div(
                    "운용모드",
                    style={
                        "fontSize": "12px",
                        "fontWeight": "500",
                        "color": "#059669",
                        "marginBottom": "8px",
                    }
                ),
                html.Div(
                    data.get("operationalMode", "---"),
                    style={
                        "fontSize": "16px",
                        "fontWeight": "700",
                        "color": "#064e3b",
                    }
                ),
            ],
            style={
                "background": "linear-gradient(to bottom right, #d1fae5, #a7f3d0)",
                "padding": "16px",
                "borderRadius": "8px",
                "border": "1px solid #a7f3d0",
            }
        ),
        # Authority (Blue)
        html.Div(
            children=[
                html.Div(
                    "운용권한",
                    style={
                        "fontSize": "12px",
                        "fontWeight": "500",
                        "color": "#2563eb",
                        "marginBottom": "8px",
                    }
                ),
                html.Div(
                    data.get("operationalAuthority", "---"),
                    style={
                        "fontSize": "16px",
                        "fontWeight": "700",
                        "color": "#1e3a8a",
                    }
                ),
            ],
            style={
                "background": "linear-gradient(to bottom right, #dbeafe, #bfdbfe)",
                "padding": "16px",
                "borderRadius": "8px",
                "border": "1px solid #bfdbfe",
            }
        ),
        # Driving State (Gray)
        html.Div(
            children=[
                html.Div(
                    "주행상태",
                    style={
                        "fontSize": "12px",
                        "fontWeight": "500",
                        "color": "#475569",
                        "marginBottom": "8px",
                    }
                ),
                html.Div(
                    data.get("drivingState", "---"),
                    style={
                        "fontSize": "16px",
                        "fontWeight": "700",
                        "color": "#0f172a",
                    }
                ),
            ],
            style={
                "background": "linear-gradient(to bottom right, #f1f5f9, #e2e8f0)",
                "padding": "16px",
                "borderRadius": "8px",
                "border": "1px solid #e2e8f0",
            }
        ),
    ]


def create_emergency_status_panel(emergency_status: Dict[str, bool]) -> dmc.Card:
    """
    Create the emergency status panel.
    
    Displays 10 emergency stop cause indicators with
    active/inactive state visualization.
    
    Args:
        emergency_status: Dictionary mapping cause names to active state
        
    Returns:
        Mantine Card component
    """
    return dmc.Card(
        children=[
            # Panel header
            html.Div(
                children=[
                    html.Div(
                        style={
                            "width": "4px",
                            "height": "16px",
                            "backgroundColor": "#f59e0b",
                            "borderRadius": "9999px",
                        }
                    ),
                    html.Div(
                        "비상정지/이상 원인",
                        style={
                            "fontSize": "14px",
                            "fontWeight": "600",
                            "color": "#334155",
                        }
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                    "marginBottom": "16px",
                }
            ),
            # Emergency indicators
            html.Div(
                id="emergency-status",
                children=create_emergency_indicators(emergency_status),
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "6px",
                }
            ),
        ],
        withBorder=True,
        p="lg",
        radius="md",
    )


def create_emergency_indicators(emergency_status: Dict[str, bool]) -> List:
    """
    Create individual emergency status indicator elements.
    
    Args:
        emergency_status: Dictionary mapping cause names to active state
        
    Returns:
        List of styled indicator divs
    """
    indicators = []
    
    for name, is_active in emergency_status.items():
        indicators.append(
            html.Div(
                children=[
                    # Status LED
                    html.Div(
                        style={
                            "width": "8px",
                            "height": "8px",
                            "borderRadius": "9999px",
                            "backgroundColor": "#ef4444" if is_active else "#cbd5e1",
                            "boxShadow": "0 0 12px rgba(239, 68, 68, 0.5)" if is_active else "none",
                        }
                    ),
                    # Label
                    html.Span(
                        name,
                        style={
                            "fontSize": "12px",
                            "fontWeight": "600" if is_active else "500",
                            "color": "#dc2626" if is_active else "#64748b",
                        }
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                    "padding": "8px 12px",
                    "borderRadius": "8px",
                    "backgroundColor": "#fee2e2" if is_active else "#f8fafc",
                    "border": f"1px solid {'#fecaca' if is_active else 'transparent'}",
                }
            )
        )
    
    return indicators


def create_device_panel(devices: List[Dict]) -> dmc.Card:
    """
    Create the device connectivity panel.
    
    Displays device grid with connection status summary.
    
    Args:
        devices: List of device status dictionaries
        
    Returns:
        Mantine Card component
    """
    from ..components.device_grid import create_device_grid
    
    connected_count = sum(1 for d in devices if d.get("connected", False))
    total_count = len(devices)
    
    return dmc.Card(
        children=[
            # Panel header with summary
            html.Div(
                children=[
                    html.Div(
                        children=[
                            html.Div(
                                style={
                                    "width": "4px",
                                    "height": "16px",
                                    "backgroundColor": "#3b82f6",
                                    "borderRadius": "9999px",
                                }
                            ),
                            html.Div(
                                "장치 연결 상태",
                                style={
                                    "fontSize": "14px",
                                    "fontWeight": "600",
                                    "color": "#334155",
                                }
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                        }
                    ),
                    html.Span(
                        f"전체: {connected_count}/{total_count} 개",
                        style={
                            "fontSize": "12px",
                            "color": "#64748b",
                        }
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "16px",
                }
            ),
            # Device grid
            html.Div(
                id="device-grid-container",
                children=[create_device_grid(devices)],
            ),
        ],
        withBorder=True,
        p="lg",
        radius="md",
        style={"marginBottom": "24px"},
    )
