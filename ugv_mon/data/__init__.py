"""Data models, providers, and type definitions for UGV-MON Dashboard.

주요 모듈:
    - packet_store: 통합 패킷 저장소 (단일 소스)
    - live_provider: 대시보드 데이터 제공
    - mock_data: 개발/테스트용 모의 데이터
    - types: TypedDict 기반 데이터 타입 정의

데이터 흐름:
    UDP → PacketQueue → PacketProcessor → PacketStore → DashboardData → UI
"""

from .packet_store import PacketRecord, PacketStore
from .types import (
    DATA_KEYS,
    AvailabilitySegment,
    ChartDataPoint,
    ConnectionState,
    DashboardData,
    DeviceStatus,
    OperationalState,
    StatsState,
    UIState,
)

__all__ = [
    "DATA_KEYS",
    "AvailabilitySegment",
    "ChartDataPoint",
    "ConnectionState",
    # Types
    "DashboardData",
    "DeviceStatus",
    "OperationalState",
    "PacketRecord",
    # Store
    "PacketStore",
    "StatsState",
    "UIState",
]
