"""
Main Dashboard Layout for UGV-MON.

Composes all layout components into the complete dashboard view.
Uses Dash Mantine Components for enterprise-grade styling.

Layout Structure:
1. Header bar (connection status, filter info)
2. KPI cards row (8 metrics)
3. Two-column main content:
   - Left: Operational status, Emergency indicators
   - Right: Device grid, Charts, Availability timeline
4. Log table (full width)
"""

from dash import dcc, html
import dash_mantine_components as dmc
from typing import Dict

from .header import create_header_bar, create_status_chips
from .panels import (
    create_operational_status_panel,
    create_operational_status_boxes,
    create_emergency_status_panel,
    create_emergency_indicators,
    create_device_panel,
)
from .charts import (
    create_communication_chart,
    create_availability_timeline,
)
from ..components.kpi_card import create_kpi_cards_row
from ..components.device_grid import create_device_grid
from ..components.log_table import create_log_table, create_log_table_header
from ..config import config


def create_main_layout(initial_data: Dict, initial_logs: list) -> dmc.MantineProvider:
    """
    Create the complete dashboard layout.
    
    Assembles all components into a single-page monitoring dashboard.
    
    Args:
        initial_data: Initial dashboard state dictionary
        initial_logs: Initial log entries for the table
        
    Returns:
        MantineProvider wrapping the complete layout
    """
    return dmc.MantineProvider(
        children=[
            # Data stores
            dcc.Store(id="dashboard-data", data=initial_data),
            dcc.Store(id="is-paused", data=False),
            dcc.Store(id="auto-scroll", data=True),
            
            # Polling interval
            dcc.Interval(
                id="interval-component",
                interval=config.ui.poll_interval_ms,
                n_intervals=0,
            ),
            
            # Main content wrapper
            html.Div(
                children=[
                    # Header Bar
                    create_header_bar(initial_data),
                    
                    # KPI Cards Row
                    html.Div(
                        id="kpi-cards",
                        children=create_kpi_cards_row(initial_data),
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(8, 1fr)",
                            "gap": "16px",
                            "marginBottom": "24px",
                        }
                    ),
                    
                    # Main Content - Two Columns
                    html.Div(
                        children=[
                            # Left Column
                            html.Div(
                                children=[
                                    create_operational_status_panel(initial_data),
                                    create_emergency_status_panel(
                                        initial_data.get("emergencyStatus", {})
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "flexDirection": "column",
                                }
                            ),
                            
                            # Right Column
                            html.Div(
                                children=[
                                    create_device_panel(
                                        initial_data.get("devices", [])
                                    ),
                                    create_charts_panel(initial_data),
                                    create_availability_panel(initial_data),
                                ],
                                style={
                                    "display": "flex",
                                    "flexDirection": "column",
                                }
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(2, 1fr)",
                            "gap": "24px",
                            "marginBottom": "24px",
                        }
                    ),
                    
                    # Log Table
                    create_log_panel(initial_logs),
                ],
                style={
                    "minHeight": "100vh",
                    "background": "linear-gradient(to bottom right, #f8fafc, #f1f5f9)",
                    "padding": "24px",
                    "fontFamily": "Inter, sans-serif",
                }
            ),
        ]
    )


def create_charts_panel(data: Dict) -> dmc.Card:
    """
    Create the communication quality charts panel.
    
    Contains combined PPS + Jitter time series charts.
    
    Args:
        data: Dashboard state with chart data
        
    Returns:
        Mantine Card with embedded Plotly chart
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
                        "통신 품질 차트",
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
            # Chart
            dcc.Graph(
                id="comm-quality-chart",
                figure=create_communication_chart(
                    data.get("combinedData", []),
                    data.get("jitterP95", 0),
                    data.get("jitterP99", 0),
                ),
                config={"displayModeBar": False},
            ),
        ],
        withBorder=True,
        p="lg",
        radius="md",
        style={"marginBottom": "24px"},
    )


def create_availability_panel(data: Dict) -> dmc.Card:
    """
    Create the availability timeline panel.
    
    Args:
        data: Dashboard state with availability segments
        
    Returns:
        Mantine Card with timeline chart
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
                        "가용성 타임라인 (1시간)",
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
                    "marginBottom": "8px",
                }
            ),
            # Timeline chart
            dcc.Graph(
                id="availability-timeline",
                figure=create_availability_timeline(
                    data.get("availabilitySegments", [])
                ),
                config={"displayModeBar": False},
            ),
        ],
        withBorder=True,
        p="lg",
        radius="md",
    )


def create_log_panel(logs: list) -> dmc.Card:
    """
    Create the log/event table panel.
    
    Args:
        logs: List of log entry dictionaries
        
    Returns:
        Mantine Card with AG-Grid table
    """
    return dmc.Card(
        children=[
            create_log_table_header(len(logs)),
            html.Div(
                children=[create_log_table(logs)],
                style={
                    "border": "1px solid #e2e8f0",
                    "borderRadius": "8px",
                    "overflow": "hidden",
                }
            ),
        ],
        withBorder=True,
        p="lg",
        radius="md",
    )
