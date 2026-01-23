"""
Dash Callbacks for UGV-MON Dashboard.

=============================================================================
대시보드의 모든 상호작용을 처리합니다:
- dcc.Interval을 통한 데이터 폴링
- UI 상태 관리 (일시정지, 초기화)
- 데이터 변경에 따른 컴포넌트 업데이트

콜백 설계:
- dcc.Store로 상태 관리
- 단일 데이터 업데이트 콜백이 컴포넌트 업데이트를 트리거
- 제어 버튼은 별도 콜백으로 순환 의존성 방지

데이터 소스 전환:
- 환경변수 UGV_MON_USE_LIVE=true: 실시간 캡처 모드
- 기본값: Mock 데이터 모드 (개발/테스트용)
=============================================================================
"""

import logging
from dash import Input, Output, State, callback, callback_context
from dash.exceptions import PreventUpdate
from typing import Dict, List, Tuple, Union

from ..data.live_provider import get_data_provider
from ..components.kpi_card import create_kpi_cards_row
from ..layouts.header import create_status_chips
from ..components.device_grid import create_device_grid
from ..layouts.panels import (
    create_operational_status_boxes,
    create_emergency_indicators,
)
from ..layouts.charts import (
    create_communication_chart,
    create_availability_timeline,
)

# 로거 설정
logger = logging.getLogger(__name__)

# =============================================================================
# 전역 데이터 제공자 인스턴스 (동적 생성)
# - register_callbacks() 호출 시 전달받은 data_provider 사용
# - 모듈 레벨에서 생성하지 않음 (환경변수 리셋 문제 해결)
# =============================================================================
_data_provider = None


def get_data_generator():
    """
    전역 데이터 제공자 인스턴스 반환.
    
    Returns:
        MockDataGenerator 또는 LiveDataProvider 인스턴스
    
    Note:
        register_callbacks() 호출 전에는 None일 수 있음
        register_callbacks() 호출 후에만 사용 가능
    """
    if _data_provider is None:
        # 폴백: 환경변수 기반으로 생성 (하위 호환성)
        return get_data_provider()
    return _data_provider


def register_callbacks(app, data_provider=None) -> None:
    """
    Register all dashboard callbacks with the Dash app.
    
    This function is called during app initialization to set up
    all interactive behaviors.
    
    Args:
        app: Dash application instance
        data_provider: 데이터 제공자 인스턴스 (None이면 환경변수 기반으로 생성)
    """
    global _data_provider
    
    # 데이터 제공자 설정
    if data_provider is None:
        _data_provider = get_data_provider()
    else:
        _data_provider = data_provider
    
    _register_data_update_callback(app)
    _register_component_update_callback(app)
    _register_control_callbacks(app)
    _register_ui_control_callbacks(app)


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
        
        return _data_provider.update_data(current_data)


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
            Output("current-pps-display", "children"),
            Output("current-jitter-display", "children"),
        ],
        [
            Input("dashboard-data", "data"),
            Input("chart-time-range", "data"),
        ],
    )
    def update_all_components(
        data: Dict,
        time_range: int
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
        # Status chips - 재사용 가능한 헬퍼 함수 사용
        status_chips = create_status_chips(data)
        
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
        
        # Charts - use time_range from store
        comm_chart = create_communication_chart(
            data.get("combinedData", []),
            data.get("jitterP95", 0),
            data.get("jitterP99", 0),
            time_range if time_range else 60,  # Default to 60 seconds
        )
        
        avail_timeline = create_availability_timeline(
            data.get("availabilitySegments", [])
        )
        
        # Log table data
        log_data = _data_provider.get_logs(limit=50)
        log_title = f"로그/이벤트 테이블 (최근 {_data_provider.log_count}개)"
        
        # Current PPS and Jitter values for display
        chart_data = data.get("combinedData", [])
        latest_pps = chart_data[-1].get("pps", 0) if chart_data else 0
        latest_jitter = chart_data[-1].get("jitter", 0) if chart_data else 0
        current_pps_text = f"{latest_pps:,}"
        current_jitter_text = f"{latest_jitter:.1f} ms"
        
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
            current_pps_text,
            current_jitter_text,
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
    
    # Time range button callbacks
    @app.callback(
        [
            Output("chart-time-range", "data"),
            Output("time-range-30s", "variant"),
            Output("time-range-1m", "variant"),
            Output("time-range-5m", "variant"),
        ],
        [
            Input("time-range-30s", "n_clicks"),
            Input("time-range-1m", "n_clicks"),
            Input("time-range-5m", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def update_time_range(
        n_clicks_30s: int,
        n_clicks_1m: int,
        n_clicks_5m: int,
    ) -> Tuple:
        """Update chart time range based on button click."""
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if button_id == "time-range-30s":
            return 30, "filled", "outline", "outline"
        elif button_id == "time-range-1m":
            return 60, "outline", "filled", "outline"
        elif button_id == "time-range-5m":
            return 300, "outline", "outline", "filled"
        else:
            raise PreventUpdate
    
    @app.callback(
        Output("dashboard-data", "data", allow_duplicate=True),
        Input("clear-btn", "n_clicks"),
        State("dashboard-data", "data"),
        prevent_initial_call=True,
    )
    def clear_logs(n_clicks: int, current_data: Dict) -> Dict:
        """Clear all log entries."""
        _data_provider.clear_logs()
        return current_data


def _register_ui_control_callbacks(app) -> None:
    """Register UI control callbacks (interface switch, connection toggle)."""
    
    @app.callback(
        Output("dashboard-data", "data", allow_duplicate=True),
        Input("interface-select", "value"),
        State("dashboard-data", "data"),
        prevent_initial_call=True,
    )
    def on_interface_change(new_interface: str, current_data: Dict) -> Dict:
        """인터페이스 변경 처리."""
        from ..data.live_provider import LiveDataProvider
        
        if isinstance(_data_provider, LiveDataProvider):
            success = _data_provider.switch_interface(new_interface)
            if success:
                logger.info(f"Interface switched to: {new_interface}")
                # 데이터 새로고침
                return _data_provider.update_data(current_data)
            else:
                logger.error(f"Failed to switch interface to: {new_interface}")
        raise PreventUpdate
    
    @app.callback(
        [
            Output("dashboard-data", "data", allow_duplicate=True),
            Output("connection-toggle-btn", "children", allow_duplicate=True),
            Output("connection-toggle-btn", "variant", allow_duplicate=True),
            Output("connection-toggle-btn", "color", allow_duplicate=True),
        ],
        Input("connection-toggle-btn", "n_clicks"),
        State("dashboard-data", "data"),
        prevent_initial_call=True,
    )
    def on_connection_toggle(n_clicks: int, current_data: Dict) -> Tuple:
        """연결 상태 토글 처리."""
        from dash import html
        from ..data.live_provider import LiveDataProvider
        
        if isinstance(_data_provider, LiveDataProvider):
            success = _data_provider.toggle_connection()
            if success:
                is_connected = _data_provider._is_connected
                logger.info(f"Connection toggled: {'Connected' if is_connected else 'Disconnected'}")
                # 데이터 새로고침
                updated_data = _data_provider.update_data(current_data)
                # 버튼 상태 업데이트
                button_children = [
                    html.Span("연결상태", style={"fontSize": "12px", "opacity": "0.7", "marginRight": "4px"}),
                    html.Span(
                        "연결됨" if is_connected else "연결끊김",
                        style={"fontSize": "12px", "fontWeight": "600"},
                    ),
                ]
                button_variant = "filled" if is_connected else "outline"
                button_color = "green" if is_connected else "red"
                return updated_data, button_children, button_variant, button_color
            else:
                logger.error("Failed to toggle connection")
        raise PreventUpdate
