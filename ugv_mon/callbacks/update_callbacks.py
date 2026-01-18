"""
Dash Callbacks for UGV-MON Dashboard.

Handles all dashboard interactivity:
- Polling data updates via dcc.Interval
- UI state management (pause, auto-scroll, clear)
- Component updates based on data changes

Callback Design:
- Uses dcc.Store for state management
- Single data update callback triggers component updates
- Separate callbacks for control buttons to avoid circular dependencies
"""

from dash import Input, Output, State, callback, callback_context
from dash.exceptions import PreventUpdate
from typing import Dict, List, Tuple

from ..data.mock_data import MockDataGenerator
from ..components.status_chip import create_status_chip
from ..components.kpi_card import create_kpi_cards_row
from ..components.device_grid import create_device_grid
from ..layouts.panels import (
    create_operational_status_boxes,
    create_emergency_indicators,
)
from ..layouts.charts import (
    create_communication_chart,
    create_availability_timeline,
)


# Global data generator instance
# In production, this will be replaced with actual capture module
_data_gen = MockDataGenerator()


def get_data_generator() -> MockDataGenerator:
    """
    Get the global data generator instance.
    
    Returns:
        MockDataGenerator instance
    """
    return _data_gen


def register_callbacks(app) -> None:
    """
    Register all dashboard callbacks with the Dash app.
    
    This function is called during app initialization to set up
    all interactive behaviors.
    
    Args:
        app: Dash application instance
    """
    _register_data_update_callback(app)
    _register_component_update_callback(app)
    _register_control_callbacks(app)


def _register_data_update_callback(app) -> None:
    """Register the main data polling callback."""
    
    @app.callback(
        Output("dashboard-data", "data"),
        Input("interval-component", "n_intervals"),
        State("dashboard-data", "data"),
        State("is-paused", "data"),
        prevent_initial_call=True,
    )
    def update_dashboard_data(
        n_intervals: int,
        current_data: Dict,
        is_paused: bool
    ) -> Dict:
        """
        Update dashboard data on each polling interval.
        
        This is the main data update callback that runs every
        poll_interval_ms (default 2000ms).
        
        Args:
            n_intervals: Number of intervals elapsed (unused, triggers update)
            current_data: Current dashboard state
            is_paused: Whether updates are paused
            
        Returns:
            Updated dashboard state dictionary
        """
        if is_paused:
            raise PreventUpdate
        
        return _data_gen.update_data(current_data)


def _register_component_update_callback(app) -> None:
    """Register the callback that updates all UI components."""
    
    @app.callback(
        [
            Output("status-chips", "children"),
            Output("kpi-cards", "children"),
            Output("operational-status", "children"),
            Output("emergency-status", "children"),
            Output("device-grid-container", "children"),
            Output("comm-quality-chart", "figure"),
            Output("availability-timeline", "figure"),
            Output("log-table", "rowData"),
            Output("log-table-title", "children"),
        ],
        Input("dashboard-data", "data"),
    )
    def update_all_components(
        data: Dict
    ) -> Tuple:
        """
        Update all dashboard components when data changes.
        
        This callback is triggered whenever dashboard-data store
        is updated, cascading updates to all visual components.
        
        Args:
            data: Updated dashboard state
            
        Returns:
            Tuple of updated component children/props
        """
        # Status chips
        status_chips = [
            create_status_chip(
                "연결상태",
                "연결됨" if data.get("connected") else "연결끊김",
                "success" if data.get("connected") else "destructive",
            ),
            create_status_chip("인터페이스", data.get("interface", "---")),
            create_status_chip("필터", data.get("filter", "---")),
            create_status_chip("마지막 패킷", data.get("lastPacketTime", "---"), "info"),
        ]
        
        # KPI cards
        kpi_cards = create_kpi_cards_row(data)
        
        # Operational status boxes
        operational_status = create_operational_status_boxes(data)
        
        # Emergency indicators
        emergency_status = create_emergency_indicators(
            data.get("emergencyStatus", {})
        )
        
        # Device grid
        device_grid = create_device_grid(data.get("devices", []))
        
        # Charts
        comm_chart = create_communication_chart(
            data.get("combinedData", []),
            data.get("jitterP95", 0),
            data.get("jitterP99", 0),
        )
        
        avail_timeline = create_availability_timeline(
            data.get("availabilitySegments", [])
        )
        
        # Log table data
        log_data = _data_gen.get_logs(limit=50)
        log_title = f"로그/이벤트 테이블 (최근 {_data_gen.log_count}개)"
        
        return (
            status_chips,
            kpi_cards,
            operational_status,
            emergency_status,
            device_grid,
            comm_chart,
            avail_timeline,
            log_data,
            log_title,
        )


def _register_control_callbacks(app) -> None:
    """Register control button callbacks."""
    
    @app.callback(
        Output("is-paused", "data"),
        Input("pause-btn", "n_clicks"),
        State("is-paused", "data"),
        prevent_initial_call=True,
    )
    def toggle_pause(n_clicks: int, is_paused: bool) -> bool:
        """Toggle pause state for data updates."""
        return not is_paused
    
    @app.callback(
        Output("pause-btn", "children"),
        Input("is-paused", "data"),
    )
    def update_pause_button_text(is_paused: bool) -> str:
        """Update pause button text based on state."""
        return "Resume" if is_paused else "Pause"
    
    @app.callback(
        Output("auto-scroll", "data"),
        Input("auto-scroll-btn", "n_clicks"),
        State("auto-scroll", "data"),
        prevent_initial_call=True,
    )
    def toggle_auto_scroll(n_clicks: int, auto_scroll: bool) -> bool:
        """Toggle auto-scroll for log table."""
        return not auto_scroll
    
    @app.callback(
        Output("dashboard-data", "data", allow_duplicate=True),
        Input("clear-btn", "n_clicks"),
        State("dashboard-data", "data"),
        prevent_initial_call=True,
    )
    def clear_logs(n_clicks: int, current_data: Dict) -> Dict:
        """Clear all log entries."""
        _data_gen.clear_logs()
        return current_data
