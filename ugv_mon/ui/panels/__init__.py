"""
ugv_mon.ui.panels — 패널 패키지 공개 인터페이스.

각 서브모듈의 공개 함수를 여기서 re-export합니다.
기존 `ugv_mon.ui.layouts.panels` import 경로는 그대로 유지됩니다.
"""

from ._common import panel_header, panel_header_inline
from .charts_panel import create_charts_panel
from .device import create_device_panel
from .emergency import (
    create_emergency_indicators,
    create_emergency_stats_content,
    create_emergency_stats_panel,
    create_emergency_status_panel,
)
from .history import (
    create_connection_history_content,
    create_connection_history_panel,
    create_mode_transitions_content,
    create_mode_transitions_panel,
)
from .log_panel import create_log_panel
from .ml_panel import create_ml_analysis_panel
from .operational import create_operational_status_boxes, create_operational_status_panel

__all__ = [
    "panel_header",
    "panel_header_inline",
    "create_charts_panel",
    "create_device_panel",
    "create_emergency_indicators",
    "create_emergency_stats_content",
    "create_emergency_stats_panel",
    "create_emergency_status_panel",
    "create_connection_history_content",
    "create_connection_history_panel",
    "create_mode_transitions_content",
    "create_mode_transitions_panel",
    "create_log_panel",
    "create_ml_analysis_panel",
    "create_operational_status_boxes",
    "create_operational_status_panel",
]
