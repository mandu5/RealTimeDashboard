"""
Main Dashboard Layout for UGV-MON.

단일 페이지 대시보드 레이아웃을 구성합니다.
나중에 멀티페이지로 확장 시 pages/dashboard.py로 이동 가능합니다.
"""

from dash import dcc, html
import dash_mantine_components as dmc
from typing import Dict

from .header import create_header_bar
from .panels import (
    create_operational_status_panel,
    create_emergency_status_panel,
    create_device_panel,
    create_charts_panel,
    create_availability_panel,
    create_log_panel,
)
from ..components.kpi_card import create_kpi_cards_row
from ..config import config
from ..styles import PAGE_CONTAINER, TWO_COLUMN_GRID, KPI_GRID, FLEX_COLUMN


def create_main_layout(initial_data: Dict, initial_logs: list) -> dmc.MantineProvider:
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
            # Notifications Provider (토스트 알림용)
            dmc.NotificationsProvider(
                id="notifications-provider",
                position="top-right",
                autoClose=5000,
                children=[
                    # 알림 트리거용 숨겨진 div
                    html.Div(id="notification-trigger", style={"display": "none"}),
                ],
            ),
            
            # 데이터 저장소
            dcc.Store(id="dashboard-data", data=initial_data),
            dcc.Store(id="is-paused", data=False),
            dcc.Store(id="chart-time-range", data=60),
            dcc.Store(id="alert-store", data=[]),  # 알림 저장소
            
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


def _create_kpi_section(data: Dict) -> html.Div:
    """KPI 카드 섹션."""
    return html.Div(
        id="kpi-cards",
        children=create_kpi_cards_row(data),
        style=KPI_GRID,
    )


def _create_main_content(data: Dict) -> html.Div:
    """메인 콘텐츠 (2컬럼 레이아웃)."""
    return html.Div(
        children=[
            # 좌측 컬럼
            html.Div(
                children=[
                    create_operational_status_panel(data),
                    create_emergency_status_panel(data.get("emergencyStatus", {})),
                ],
                style=FLEX_COLUMN,
            ),
            # 우측 컬럼
            html.Div(
                children=[
                    create_device_panel(data.get("devices", [])),
                    create_charts_panel(data),
                    create_availability_panel(data),
                ],
                style=FLEX_COLUMN,
            ),
        ],
        style=TWO_COLUMN_GRID,
    )
