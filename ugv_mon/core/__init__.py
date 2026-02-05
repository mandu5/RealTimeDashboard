"""
UGV-MON 핵심 모듈.

이 패키지는 프로젝트 전체에서 사용되는 핵심 기능을 제공합니다:
    - models: 데이터 클래스 및 열거형
    - config: 앱 설정
    - constants: 상수 정의
"""

from .models import (
    # 열거형
    MsgCode,
    AckFlag,
    DeviceID,
    OperationMode,
    Authority,
    DrivingState,
    # 매핑 테이블
    OPERATION_MODES,
    AUTHORITIES,
    DRIVING_STATES,
    DEVICE_BIT_NAMES,
    EMERGENCY_SOURCE_NAMES,
    # ICD 모델
    ICDHeader,
    OperationalPayload,
    ParseResult,
    # UI 모델
    DeviceStatus,
    LogEntry,
    AvailabilitySegment,
    EmergencyStatus,
)

from .config import config
from .constants import (
    DEVICE_IDS,
    DEVICE_NAMES,
    DEVICE_ID_TO_NAME,
    DEFAULT_INITIAL_SEQUENCE,
    SEQ_MODULO,
    EXPECTED_PPS,
    ICD_HEADER_SIZE,
    ICD_CHECKSUM_SIZE,
    ICD_MIN_PACKET_SIZE,
)

__all__ = [
    # 열거형
    "MsgCode", "AckFlag", "DeviceID", "OperationMode", "Authority", "DrivingState",
    # 매핑
    "OPERATION_MODES", "AUTHORITIES", "DRIVING_STATES", "DEVICE_BIT_NAMES", "EMERGENCY_SOURCE_NAMES",
    # 모델
    "ICDHeader", "OperationalPayload", "ParseResult",
    "DeviceStatus", "LogEntry", "AvailabilitySegment", "EmergencyStatus",
    # 설정/상수
    "config",
    "DEVICE_IDS", "DEVICE_NAMES", "DEVICE_ID_TO_NAME",
    "DEFAULT_INITIAL_SEQUENCE", "SEQ_MODULO", "EXPECTED_PPS",
    "ICD_HEADER_SIZE", "ICD_CHECKSUM_SIZE", "ICD_MIN_PACKET_SIZE",
]
