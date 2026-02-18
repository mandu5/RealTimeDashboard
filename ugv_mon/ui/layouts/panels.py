"""
패널 모듈 — 하위 호환 re-export 파사드.

실제 구현은 ugv_mon/ui/panels/ 패키지로 이동했습니다.
기존 import 경로(ugv_mon.ui.layouts.panels)는 그대로 유지됩니다.
"""

from ..panels import (  # noqa: F401
    create_charts_panel,
    create_connection_history_content,
    create_connection_history_panel,
    create_device_panel,
    create_emergency_indicators,
    create_emergency_stats_content,
    create_emergency_stats_panel,
    create_emergency_status_panel,
    create_log_panel,
    create_ml_analysis_panel,
    create_mode_transitions_content,
    create_mode_transitions_panel,
    create_operational_status_boxes,
    create_operational_status_panel,
    panel_header,
    panel_header_inline,
)
