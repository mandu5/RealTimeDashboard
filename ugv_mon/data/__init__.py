"""Data models, providers, and type definitions for UGV-MON Dashboard.

주요 모듈:
    - packet_store: 통합 패킷 저장소 (단일 소스)
    - live_provider: 대시보드 데이터 제공
    - mock_data: 개발/테스트용 모의 데이터
    - types: TypedDict 기반 데이터 타입 정의

데이터 흐름:
    UDP → PacketQueue → PacketProcessor → PacketStore → DashboardData → UI
"""

from .types import (
    DashboardData,
    ConnectionState,
    StatsState,
    OperationalState,
    UIState,
    ChartDataPoint,
    AvailabilitySegment,
    DeviceStatus,
    DATA_KEYS,
)

from .packet_store import PacketStore, PacketRecord

__all__ = [
    # Types
    "DashboardData",
    "ConnectionState",
    "StatsState",
    "OperationalState",
    "UIState",
    "ChartDataPoint",
    "AvailabilitySegment",
    "DeviceStatus",
    "DATA_KEYS",
    # Store
    "PacketStore",
    "PacketRecord",
]
