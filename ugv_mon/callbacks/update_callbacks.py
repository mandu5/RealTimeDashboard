"""
Dash Callbacks for UGV-MON Dashboard.

대시보드의 모든 상호작용을 처리합니다.
클로저(Closure)를 통해 data_provider를 캡처합니다 (전역 상태 제거).
"""

import logging
from dash import Input, Output, State, callback_context, html
from dash.exceptions import PreventUpdate
from typing import Dict, Tuple, Protocol, List

from ..components.kpi_card import create_kpi_cards_row
from ..layouts.header import create_status_chips
from ..components.device_grid import create_device_grid
from ..layouts.panels import create_operational_status_boxes, create_emergency_indicators
from ..layouts.charts import create_communication_chart, create_availability_timeline

logger = logging.getLogger(__name__)


class DataProviderProtocol(Protocol):
    """데이터 제공자 인터페이스."""
    def update_data(self, prev_data: Dict) -> Dict: ...
    def get_logs(self, limit: int = 50) -> List[Dict]: ...
    def clear_logs(self) -> None: ...
    @property
    def log_count(self) -> int: ...


def register_callbacks(app, data_provider: DataProviderProtocol) -> None:
    """모든 대시보드 콜백 등록."""
    if data_provider is None:
        raise ValueError("data_provider cannot be None")
    
    _register_data_callback(app, data_provider)
    _register_component_callback(app, data_provider)
    _register_control_callbacks(app, data_provider)
    _register_ui_callbacks(app, data_provider)


def _register_data_callback(app, provider) -> None:
    """데이터 폴링 콜백."""
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
    """UI 컴포넌트 업데이트 콜백."""
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
            Output("current-pps-display", "children"),
            Output("current-jitter-display", "children"),
        ],
        [Input("dashboard-data", "data"), Input("chart-time-range", "data")],
    )
    def update_components(data, time_range):
        chart_data = data.get("combinedData", [])
        latest = chart_data[-1] if chart_data else {"pps": 0, "jitter": 0}
        
        return (
            create_status_chips(data),
            create_kpi_cards_row(data),
            create_operational_status_boxes(data),
            create_emergency_indicators(data.get("emergencyStatus", {})),
            create_device_grid(data.get("devices", [])),
            create_communication_chart(chart_data, data.get("jitterP95", 0), data.get("jitterP99", 0), time_range or 60),
            create_availability_timeline(data.get("availabilitySegments", [])),
            provider.get_logs(limit=50),
            f"로그/이벤트 테이블 (최근 {provider.log_count}개)",
            f"{latest.get('pps', 0):,}",
            f"{latest.get('jitter', 0):.1f} ms",
        )


def _register_control_callbacks(app, provider) -> None:
    """제어 버튼 콜백."""
    @app.callback(Output("is-paused", "data"), Input("pause-btn", "n_clicks"), State("is-paused", "data"), prevent_initial_call=True)
    def toggle_pause(n_clicks, is_paused):
        return not is_paused
    
    @app.callback(Output("pause-btn", "children"), Input("is-paused", "data"))
    def update_pause_text(is_paused):
        return "Resume" if is_paused else "Pause"
    
    @app.callback(
        [Output("chart-time-range", "data"), Output("time-range-30s", "variant"), Output("time-range-1m", "variant"), Output("time-range-5m", "variant")],
        [Input("time-range-30s", "n_clicks"), Input("time-range-1m", "n_clicks"), Input("time-range-5m", "n_clicks")],
        prevent_initial_call=True,
    )
    def update_time_range(n30, n1m, n5m):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        btn = ctx.triggered[0]["prop_id"].split(".")[0]
        mappings = {"time-range-30s": (30, "filled", "outline", "outline"), "time-range-1m": (60, "outline", "filled", "outline"), "time-range-5m": (300, "outline", "outline", "filled")}
        return mappings.get(btn, (60, "outline", "filled", "outline"))
    
    @app.callback(Output("dashboard-data", "data", allow_duplicate=True), Input("clear-btn", "n_clicks"), State("dashboard-data", "data"), prevent_initial_call=True)
    def clear_logs(n_clicks, current_data):
        provider.clear_logs()
        return current_data


def _register_ui_callbacks(app, provider) -> None:
    """UI 제어 콜백 (인터페이스 전환, 연결 토글)."""
    @app.callback(Output("dashboard-data", "data", allow_duplicate=True), Input("interface-select", "value"), State("dashboard-data", "data"), prevent_initial_call=True)
    def on_interface_change(new_interface, current_data):
        if hasattr(provider, 'switch_interface') and provider.switch_interface(new_interface):
            logger.info(f"Interface switched to: {new_interface}")
            return provider.update_data(current_data)
        raise PreventUpdate
    
    @app.callback(
        [Output("dashboard-data", "data", allow_duplicate=True), Output("connection-toggle-btn", "children", allow_duplicate=True), Output("connection-toggle-btn", "variant", allow_duplicate=True), Output("connection-toggle-btn", "color", allow_duplicate=True)],
        Input("connection-toggle-btn", "n_clicks"), State("dashboard-data", "data"), prevent_initial_call=True,
    )
    def on_connection_toggle(n_clicks, current_data):
        if not hasattr(provider, 'toggle_connection'):
            raise PreventUpdate
        if provider.toggle_connection():
            is_conn = getattr(provider, '_is_connected', False)
            return (
                provider.update_data(current_data),
                [html.Span("연결상태", style={"fontSize": "12px", "opacity": "0.7", "marginRight": "4px"}), html.Span("연결됨" if is_conn else "연결끊김", style={"fontSize": "12px", "fontWeight": "600"})],
                "filled" if is_conn else "outline",
                "green" if is_conn else "red",
            )
        logger.error("Failed to toggle connection")
        raise PreventUpdate
