"""Dash 콜백 모듈 - 대시보드 상호작용 처리."""

import logging
import time
from typing import Any, Protocol

from dash import Dash, Input, Output, State, html, no_update
from dash.exceptions import PreventUpdate

from ..config import config
from ..constants import ML_DEFAULT_THRESHOLD
from ..ui.components.device_grid import create_device_grid
from ..ui.components.kpi_card import create_kpi_cards_row
from ..ui.layouts.charts import create_communication_chart
from ..ui.layouts.header import create_status_chips
from ..ui.layouts.panels import (
    create_connection_history_content,
    create_emergency_indicators,
    create_emergency_stats_content,
    create_ml_analysis_panel,
    create_mode_transitions_content,
    create_operational_status_boxes,
)

logger = logging.getLogger(__name__)


def _connection_btn_children(is_conn: bool) -> list:
    """연결 상태 토글 버튼 자식 요소 생성."""
    return [
        html.Span("연결상태", style={"fontSize": "12px", "opacity": "0.7", "marginRight": "4px"}),
        html.Span("연결됨" if is_conn else "연결끊김", style={"fontSize": "12px", "fontWeight": "600"}),
    ]


class DataProviderProtocol(Protocol):
    """데이터 제공자 인터페이스.

    콜백에서 사용. provider._is_connected 속성으로 연결 상태 조회.
    """
    def update_data(self, prev_data: dict[str, Any]) -> dict[str, Any]: ...
    def clear_logs(self) -> None: ...


def register_callbacks(app: Dash, data_provider: DataProviderProtocol) -> None:
    """모든 대시보드 콜백 등록."""
    if data_provider is None:
        raise ValueError("data_provider cannot be None")

    _register_data_callback(app, data_provider)
    _register_component_callback(app, data_provider)
    _register_control_callbacks(app, data_provider)
    _register_ui_callbacks(app, data_provider)
    _register_ml_panel_callback(app)
    _register_ml_3d_interaction_callback(app)



def _register_data_callback(app: Dash, provider: DataProviderProtocol) -> None:
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


def _register_component_callback(app: Dash, provider: DataProviderProtocol) -> None:
    """메인 UI 컴포넌트 업데이트."""
    @app.callback(
        [
            Output("status-chips", "children"),
            Output("kpi-cards", "children"),
            Output("operational-status", "children"),
            Output("emergency-status", "children"),
            Output("device-grid-container", "children"),
            Output("comm-quality-chart", "figure"),
            Output("current-pps-display", "children"),
            Output("current-jitter-display", "children"),
            Output("connection-toggle-btn", "children"),
            Output("connection-toggle-btn", "variant"),
            Output("connection-toggle-btn", "color"),
            # 연결 이력, 모드 전이, 비상정지 통계 패널
            Output("connection-history-container", "children"),
            Output("mode-transitions-container", "children"),
            Output("emergency-stats-container", "children"),
            Output("ml-analysis-container", "children"),
            Output("log-table", "rowData"),
            Output("log-table-title", "children"),
        ],
        Input("dashboard-data", "data"),
    )
    def update_main_components(data):
        if data is None:
            data = {}
        chart_data = data.get("combinedData", [])
        latest = chart_data[-1] if chart_data else {"pps": 0, "jitter": 0}
        is_conn = data.get("connected", False)

        return (
            create_status_chips(data),
            create_kpi_cards_row(data),
            create_operational_status_boxes(data),
            create_emergency_indicators(data.get("emergencyStatus", {})),
            create_device_grid(data.get("devices", [])),
            create_communication_chart(chart_data, data.get("jitterP95", 0), config.ui.chart_time_range_sec),
            f"{latest.get('pps', 0):,}",
            f"{latest.get('jitter', 0):.1f} ms",
            _connection_btn_children(is_conn),
            "filled" if is_conn else "outline",
            "green" if is_conn else "red",
            # 연결 이력, 모드 전이, 비상정지 컨텐츠
            create_connection_history_content(data),
            create_mode_transitions_content(data),
            create_emergency_stats_content(data),
            create_ml_analysis_panel(data),
            data.get("logs", []),
            f"로그/이벤트 테이블 (최근 {len(data.get('logs', []))}개)",
        )


def _register_control_callbacks(app: Dash, provider: DataProviderProtocol) -> None:
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


def _register_ui_callbacks(app: Dash, provider: DataProviderProtocol) -> None:
    """UI 제어 콜백 (연결, 방향)."""
    @app.callback(
        [
            Output("connection-toggle-btn", "children", allow_duplicate=True),
            Output("connection-toggle-btn", "variant", allow_duplicate=True),
            Output("connection-toggle-btn", "color", allow_duplicate=True),
            Output("dashboard-data", "data", allow_duplicate=True),
        ],
        Input("connection-toggle-btn", "n_clicks"),
        State("dashboard-data", "data"),
        prevent_initial_call=True,
    )
    def on_connection_toggle(n_clicks, current_data):
        if not hasattr(provider, 'toggle_connection'):
            raise PreventUpdate
        provider.toggle_connection()
        new_data = provider.update_data(current_data or {})
        is_conn = new_data.get("connected", False)
        return (
            _connection_btn_children(is_conn),
            "filled" if is_conn else "outline",
            "green" if is_conn else "red",
            new_data,
        )

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


def _register_ml_3d_interaction_callback(app: Dash) -> None:
    """3D 차트 relayout 시 타임스탬프 저장 (드래그/줌 중 폴링 억제용)."""
    app.clientside_callback(
        """
        function(relayoutData) {
            if (relayoutData && Object.keys(relayoutData).length > 0) {
                return Date.now();
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("ml-3d-relayout-ts", "data"),
        Input("ml-3d-scatter", "relayoutData"),
        prevent_initial_call=True,
    )


def _register_ml_panel_callback(app: Dash) -> None:
    """ML 패널 업데이트 콜백."""
    from ..ui.layouts.ml_charts import (
        create_anomaly_3d_scatter,
        create_anomaly_timeline,
        create_confidence_gauge,
        create_feature_contribution_chart,
    )

    @app.callback(
        [
            Output("ml-3d-scatter", "figure"),
            Output("ml-anomaly-timeline", "figure"),
            Output("ml-feature-contribution", "figure"),
            Output("ml-confidence-gauge", "figure"),
        ],
        Input("dashboard-data", "data"),
        State("ml-3d-relayout-ts", "data"),
    )
    def update_ml_panel(data, relayout_ts):
        ml_data = data.get("ml", {})
        if ml_data.get("model_status", "not_ready") == "not_ready":
            raise PreventUpdate
        records = ml_data.get("records", [])
        score_history = ml_data.get("score_history", [])
        contributing_features = ml_data.get("contributing_features", [])
        confidence = ml_data.get("confidence", 0)
        threshold = ml_data.get("threshold", ML_DEFAULT_THRESHOLD)
        anomaly_scores = [r.get("anomaly_score", 0) for r in records] if records else []

        timeline_fig = create_anomaly_timeline(score_history, threshold)
        feature_fig = create_feature_contribution_chart(contributing_features)
        confidence_fig = create_confidence_gauge(confidence)

        # 드래그/줌 중일 때는 3D 업데이트 건너뜀 (2.5초 이내 relayout 있으면)
        now_ms = int(time.time() * 1000)
        if relayout_ts and (now_ms - relayout_ts) < 2500:
            return (
                no_update,
                timeline_fig,
                feature_fig,
                confidence_fig,
            )

        scatter_fig = create_anomaly_3d_scatter(records, anomaly_scores, threshold)
        return (
            scatter_fig,
            timeline_fig,
            feature_fig,
            confidence_fig,
        )
