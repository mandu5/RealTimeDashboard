"""
UGV-MON 패널 모듈.

각 패널을 개별 파일로 분리하여 관리합니다.
"""

# 운용 상태
from .operational import create_operational_status_panel, create_operational_status_boxes

# 비상정지
from .emergency import create_emergency_status_panel, create_emergency_indicators

# 장치 연결
from .device import create_device_panel

# 차트 및 가용성
from .charts import create_charts_panel, create_availability_panel

# 이력 및 통계 (Phase 3-6)
from .history import (
    create_msg_code_stats_panel,
    create_connection_history_panel,
    create_connection_history_content,
    create_mode_transitions_panel,
    create_mode_transitions_content,
    create_emergency_stats_panel,
    create_emergency_stats_content,
)

# 로그 테이블
from .logs import create_log_panel


__all__ = [
    # 운용 상태
    "create_operational_status_panel",
    "create_operational_status_boxes",
    # 비상정지
    "create_emergency_status_panel",
    "create_emergency_indicators",
    # 장치
    "create_device_panel",
    # 차트
    "create_charts_panel",
    "create_availability_panel",
    # 이력/통계
    "create_msg_code_stats_panel",
    "create_connection_history_panel",
    "create_connection_history_content",
    "create_mode_transitions_panel",
    "create_mode_transitions_content",
    "create_emergency_stats_panel",
    "create_emergency_stats_content",
    # 로그
    "create_log_panel",
]
