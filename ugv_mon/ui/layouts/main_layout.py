"""
Main Dashboard Layout for UGV-MON.

단일 페이지 대시보드 레이아웃을 구성합니다.
나중에 멀티페이지로 확장 시 pages/dashboard.py로 이동 가능합니다.
"""


import dash_mantine_components as dmc
from dash import dcc, html

from ..components.kpi_card import create_kpi_cards_row
from ...config import config
from ...styles import FLEX_COLUMN, KPI_GRID, PAGE_CONTAINER, TWO_COLUMN_GRID
from .header import create_header_bar
from .panels import (
    create_availability_panel,
    create_charts_panel,
    create_connection_history_panel,
    create_device_panel,
    create_emergency_stats_panel,
    create_emergency_status_panel,
    create_log_panel,
    create_ml_analysis_panel,
    create_mode_transitions_panel,
    create_operational_status_panel,
)


def create_main_layout(initial_data: dict, initial_logs: list) -> dmc.MantineProvider:
    """
    대시보드 메인 레이아웃 생성.

    Args:
        initial_data: 초기 대시보드 상태
        initial_logs: 초기 로그 엔트리

    Returns:
        MantineProvider로 래핑된 레이아웃
    """
    return dmc.MantineProvider(
        children=[
            # 데이터 저장소
            dcc.Store(id="dashboard-data", data=initial_data),
            # is-paused: 클라이언트(브라우저) 탭별 독립 UI 상태.
            # - dcc.Store는 브라우저 세션 메모리(JS 변수)이며 DB가 아님.
            # - 서버 config/constants에 넣으면 모든 클라이언트가 상태를 공유하게 되어 부적합.
            # - 각 브라우저 탭마다 독립적인 일시정지 상태가 필요하므로 dcc.Store가 정답.
            # - 새로고침 시 초기값(False)으로 자동 리셋됨.
            # - Dash 공식 패턴: 콜백 간 클라이언트 상태 공유에 dcc.Store 사용 권장.
            dcc.Store(id="is-paused", data=False),

            # 폴링 인터벌
            dcc.Interval(
                id="interval-component",
                interval=config.ui.poll_interval_ms,
                n_intervals=0,
            ),

            # 메인 컨텐츠
            html.Div(
                children=[
                    create_header_bar(initial_data),
                    _create_kpi_section(initial_data),
                    _create_main_content(initial_data),
                    create_log_panel(initial_logs),
                ],
                style=PAGE_CONTAINER,
            ),
        ]
    )


def _create_kpi_section(data: dict) -> html.Div:
    """KPI 카드 섹션."""
    return html.Div(
        id="kpi-cards",
        children=create_kpi_cards_row(data),
        style=KPI_GRID,
    )


def _create_main_content(data: dict) -> html.Div:
    """메인 콘텐츠 (2컬럼 레이아웃)."""
    return html.Div(
        children=[
            # 좌측 컬럼
            html.Div(
                children=[
                    create_operational_status_panel(data),
                    create_emergency_status_panel(data.get("emergencyStatus", {})),
                    create_emergency_stats_panel(data),  # Phase 6
                    create_mode_transitions_panel(data),  # Phase 5
                    create_connection_history_panel(data),  # Phase 4
                ],
                style=FLEX_COLUMN,
            ),
            # 우측 컬럼
            html.Div(
                children=[
                    create_device_panel(data.get("devices", [])),
                    create_charts_panel(data),
                    create_availability_panel(data),
                    create_ml_analysis_panel(data),  # ML 이상 탐지
                ],
                style=FLEX_COLUMN,
            ),
        ],
        style=TWO_COLUMN_GRID,
    )
