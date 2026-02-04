"""Dash 콜백 모듈 - 대시보드 상호작용 처리."""

import logging
from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate
from typing import Dict, Protocol, List

from ..components.kpi_card import create_kpi_cards_row
from ..layouts.header import create_status_chips
from ..components.device_grid import create_device_grid
from ..layouts.panels import create_operational_status_boxes, create_emergency_indicators
from ..layouts.charts import create_communication_chart, create_availability_timeline

logger = logging.getLogger(__name__)


class DataProviderProtocol(Protocol):
    """데이터 제공자 인터페이스."""
    def update_data(self, prev_data: Dict) -> Dict: ...
    def clear_logs(self) -> None: ...


def register_callbacks(app, data_provider: DataProviderProtocol) -> None:
    """모든 대시보드 콜백 등록."""
    if data_provider is None:
        raise ValueError("data_provider cannot be None")
    
    _register_data_callback(app, data_provider)
    _register_component_callback(app, data_provider)
    _register_control_callbacks(app, data_provider)
    _register_ui_callbacks(app, data_provider)


def _register_data_callback(app, provider) -> None:
    """데이터 폴링 콜백 (2초 interval)."""
    @app.callback(
        Output("dashboard-data", "data"),
        Input("interval-component", "n_intervals"),
        State("dashboard-data", "data"),
        State("is-paused", "data"),
        prevent_initial_call=True,
    )
    def update_data(n_intervals, current_data, is_paused):
        if is_paused:
            raise PreventUpdate
        return provider.update_data(current_data)


def _register_component_callback(app, provider) -> None:
    """메인 UI 컴포넌트 업데이트."""
    @app.callback(
        [
            Output("status-chips", "children"),
            Output("kpi-cards", "children"),
            Output("operational-status", "children"),
            Output("emergency-status", "children"),
            Output("device-grid-container", "children"),
            Output("comm-quality-chart", "figure"),
            Output("availability-timeline", "figure"),
            Output("current-pps-display", "children"),
            Output("current-jitter-display", "children"),
            Output("connection-toggle-btn", "children"),
            Output("connection-toggle-btn", "variant"),
            Output("connection-toggle-btn", "color"),
        ],
        Input("dashboard-data", "data"),
    )
    def update_main_components(data):
        chart_data = data.get("combinedData", [])
        latest = chart_data[-1] if chart_data else {"pps": 0, "jitter": 0}
        is_conn = getattr(provider, '_is_connected', False)
        
        btn_children = [
            html.Span("연결상태", style={"fontSize": "12px", "opacity": "0.7", "marginRight": "4px"}),
            html.Span("연결됨" if is_conn else "연결끊김", style={"fontSize": "12px", "fontWeight": "600"}),
        ]
        
        return (
            create_status_chips(data),
            create_kpi_cards_row(data),
            create_operational_status_boxes(data),
            create_emergency_indicators(data.get("emergencyStatus", {})),
            create_device_grid(data.get("devices", [])),
            create_communication_chart(chart_data, data.get("jitterP95", 0), data.get("jitterP99", 0), 60),
            create_availability_timeline(data.get("availabilitySegments", [])),
            f"{latest.get('pps', 0):,}",
            f"{latest.get('jitter', 0):.1f} ms",
            btn_children,
            "filled" if is_conn else "outline",
            "green" if is_conn else "red",
        )


def _register_control_callbacks(app, provider) -> None:
    """제어 버튼 콜백."""
    @app.callback(Output("is-paused", "data"), Input("pause-btn", "n_clicks"), 
                  State("is-paused", "data"), prevent_initial_call=True)
    def toggle_pause(n_clicks, is_paused):
        return not is_paused
    
    @app.callback(Output("pause-btn", "children"), Input("is-paused", "data"))
    def update_pause_text(is_paused):
        return "Resume" if is_paused else "Pause"
    
    @app.callback(Output("dashboard-data", "data", allow_duplicate=True),
                  Input("clear-btn", "n_clicks"), State("dashboard-data", "data"), prevent_initial_call=True)
    def clear_logs(n_clicks, current_data):
        provider.clear_logs()
        return current_data


def _register_ui_callbacks(app, provider) -> None:
    """UI 제어 콜백 (인터페이스, 연결, 방향)."""
    @app.callback(Output("dashboard-data", "data", allow_duplicate=True),
                  Input("interface-select", "value"), State("dashboard-data", "data"), prevent_initial_call=True)
    def on_interface_change(new_interface, current_data):
        if hasattr(provider, 'switch_interface') and provider.switch_interface(new_interface):
            logger.info(f"Interface switched to: {new_interface}")
            return provider.update_data(current_data)
        raise PreventUpdate
    
    @app.callback(
        [Output("connection-toggle-btn", "children", allow_duplicate=True),
         Output("connection-toggle-btn", "variant", allow_duplicate=True),
         Output("connection-toggle-btn", "color", allow_duplicate=True)],
        Input("connection-toggle-btn", "n_clicks"), prevent_initial_call=True,
    )
    def on_connection_toggle(n_clicks):
        if not hasattr(provider, 'toggle_connection'):
            raise PreventUpdate
        is_conn = provider.toggle_connection()
        btn_children = [
            html.Span("연결상태", style={"fontSize": "12px", "opacity": "0.7", "marginRight": "4px"}),
            html.Span("연결됨" if is_conn else "연결끊김", style={"fontSize": "12px", "fontWeight": "600"}),
        ]
        return (btn_children, "filled" if is_conn else "outline", "green" if is_conn else "red")
    
    @app.callback(
        [Output("direction-toggle-btn", "children", allow_duplicate=True),
         Output("direction-toggle-btn", "color", allow_duplicate=True)],
        Input("direction-toggle-btn", "n_clicks"), prevent_initial_call=True,
    )
    def on_direction_toggle(n_clicks):
        if not hasattr(provider, 'toggle_direction'):
            raise PreventUpdate
        direction = provider.toggle_direction()
        label = "상태(50000→61000)" if direction == "status" else "제어(61000→50000)"
        children = [
            html.Span("방향", style={"fontSize": "12px", "opacity": "0.7", "marginRight": "4px"}),
            html.Span(label, style={"fontSize": "12px", "fontWeight": "600"}),
        ]
        return children, "blue" if direction == "status" else "orange"
