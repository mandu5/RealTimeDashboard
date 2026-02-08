"""
UGV-MON 핵심 모듈.

이 패키지는 프로젝트 전체에서 사용되는 핵심 기능을 제공합니다:
    - models: 데이터 클래스 및 열거형
    - config: 앱 설정
    - constants: 상수 정의
"""

from .config import config
from .constants import (
    DEFAULT_INITIAL_SEQUENCE,
    DEVICE_ID_TO_NAME,
    DEVICE_IDS,
    DEVICE_NAMES,
    EXPECTED_PPS,
    ICD_CHECKSUM_SIZE,
    ICD_HEADER_SIZE,
    ICD_MIN_PACKET_SIZE,
    SEQ_MODULO,
)
from .models import (
    AUTHORITIES,
    DEVICE_BIT_NAMES,
    DRIVING_STATES,
    EMERGENCY_SOURCE_NAMES,
    # 매핑 테이블
    OPERATION_MODES,
    AckFlag,
    Authority,
    AvailabilitySegment,
    DeviceID,
    # UI 모델
    DeviceStatus,
    DrivingState,
    # ICD 모델
    ICDHeader,
    LogEntry,
    # 열거형
    MsgCode,
    OperationalPayload,
    OperationMode,
    ParseResult,
    # 헬퍼
    build_default_emergency_dict,
)

__all__ = [
    "AUTHORITIES",
    "DEFAULT_INITIAL_SEQUENCE",
    "DEVICE_BIT_NAMES",
    "DEVICE_IDS",
    "DEVICE_ID_TO_NAME",
    "DEVICE_NAMES",
    "DRIVING_STATES",
    "EMERGENCY_SOURCE_NAMES",
    "EXPECTED_PPS",
    "ICD_CHECKSUM_SIZE",
    "ICD_HEADER_SIZE",
    "ICD_MIN_PACKET_SIZE",
    # 매핑
    "OPERATION_MODES",
    "SEQ_MODULO",
    "AckFlag",
    "Authority",
    "AvailabilitySegment",
    "DeviceID",
    "DeviceStatus",
    "DrivingState",
    # 모델
    "ICDHeader",
    "LogEntry",
    # 열거형
    "MsgCode",
    "OperationMode",
    "OperationalPayload",
    "ParseResult",
    "build_default_emergency_dict",
    # 설정/상수
    "config",
]
