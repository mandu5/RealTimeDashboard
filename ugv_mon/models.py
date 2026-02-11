"""
UGV-MON 통합 데이터 모델.

이 모듈은 프로젝트 전체에서 사용되는 모든 데이터 클래스를 정의합니다.

구성:
    1. 열거형 (Enums) - 메시지 코드, 운용 모드, 권한 등
    2. ICD 파싱 모델 - 헤더, 페이로드, 파싱 결과
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, IntEnum
from typing import Optional, Union

# =============================================================================
# 1. 열거형 정의 (Enums)
# =============================================================================

class MsgCode(IntEnum):
    """ICD 메시지 코드.

    VIC-OCS 통신에서 사용되는 메시지 타입을 정의합니다.

    Attributes:
        TYPE_01: 운용 상태 메시지 (VIC→OCS, data_length=87)
        REMOTE_CONTROL: 원격 제어 메시지 (OCS→VIC, 80~110Hz)
        TYPE_25: Heartbeat 메시지
        TYPE_40: 예약됨
    """
    TYPE_01 = 0x01
    REMOTE_CONTROL = 0x10
    TYPE_25 = 0x25
    TYPE_40 = 0x40


class AckFlag(IntEnum):
    """ACK 요청 플래그."""
    REQUESTED = 0x00
    NOT_REQUESTED = 0xFF


class DeviceID(IntEnum):
    """장치 ID.

    Attributes:
        VIC: 차량 통합 컴퓨터 (0xB1, 포트 50000)
        OCS: 운용통제장치 (0xA2, 포트 61000)
    """
    VIC = 0xB1
    OCS = 0xA2


class OperationMode(Enum):
    """운용 모드 (3비트: bits 7..5)."""
    PREP = 0b000              # 준비
    TRANSITION = 0b001        # 전환 중
    UNMANNED_DRIVING = 0b010  # 무인 주행
    UNMANNED_FIRING = 0b011   # 무인 사격
    EMERGENCY_STOP = 0b100    # 비상 정지
    UNKNOWN = 0xFF


class Authority(Enum):
    """운용 권한 (2비트: bits 3..2)."""
    RELEASED = 0b00           # 권한 해제
    OCS_ACQUIRED = 0b01       # OCS 획득
    NEAR_CONTROLLER = 0b10    # 근거리 조종기
    UNKNOWN = 0xFF


class DrivingState(Enum):
    """주행 상태 (2비트: bits 1..0)."""
    REMOTE = 0b01             # 원격 주행
    PLATOONING = 0b10         # 군집 주행
    AUTONOMOUS_DISPATCH = 0b11  # 자율 배차
    UNKNOWN = 0xFF


# =============================================================================
# 2. 매핑 테이블 (상수)
# =============================================================================

# 운용 모드 한글 매핑
OPERATION_MODES = {
    0: "준비",
    1: "무인주행",
    2: "유인주행",
    3: "비상정지",
    4: "점검",
    5: "원격"
}

# 운용 권한 한글 매핑
AUTHORITIES = {
    0: "없음",
    1: "OCS(운용통제기)",
    2: "근거리조종기",
    3: "VIC"
}

# 주행 상태 한글 매핑
DRIVING_STATES = {
    0: "정지",
    1: "전진",
    2: "후진",
    3: "회전"
}

# 장치 비트 순서 (10개)
DEVICE_BIT_NAMES = ["VIC", "RDC", "ADC", "FCAM", "RCAM", "ACAM", "SCS", "DIP", "TCC", "TM"]

# 비상정지 원인 비트 순서
EMERGENCY_SOURCE_NAMES = [
    "미식별", "운전자", "원격", "장애물", "경사",
    "속도초과", "통신이상", "배터리", "엔진", "기타"
]


# =============================================================================
# 3. ICD 파싱 모델
# =============================================================================

@dataclass
class ICDHeader:
    """ICD v1.0 헤더 (12 bytes).

    모든 VIC-OCS 메시지의 공통 헤더 구조입니다.

    Attributes:
        timestamp: VIC 시스템 타임스탬프 (ms)
        sequence: 시퀀스 번호 (0~15, 롤오버)
        source_id: 송신 장치 ID
        dest_id: 수신 장치 ID
        msg_code: 메시지 타입
        ack_flag: ACK 요청 플래그
        reserved: 예약 (항상 0x00)
        data_length: 페이로드 길이 (bytes)
    """
    timestamp: int
    sequence: int
    source_id: Union[DeviceID, int]
    dest_id: Union[DeviceID, int]
    msg_code: Union[MsgCode, int]
    ack_flag: Union[AckFlag, int]
    reserved: int
    data_length: int

    def to_dict(self) -> dict:
        """딕셔너리 변환 (디버깅/로깅용)."""
        def fmt(val, enum_cls):
            if isinstance(val, enum_cls):
                return f"{val.name} (0x{val:02X})"
            return f"UNKNOWN (0x{val:02X})"

        return {
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "source_id": fmt(self.source_id, DeviceID),
            "dest_id": fmt(self.dest_id, DeviceID),
            "msg_code": fmt(self.msg_code, MsgCode),
            "ack_flag": fmt(self.ack_flag, AckFlag),
            "data_length": self.data_length,
        }


@dataclass
class OperationalPayload:
    """운용 상태 페이로드 (MsgCode 0x01, 87 bytes).

    VIC에서 OCS로 전송되는 운용 상태 정보입니다.

    Attributes:
        device_bits: 장치 연결 비트맵 (10 bits)
        devices: 장치명 → 연결 상태 딕셔너리
        operation_mode: 현재 운용 모드 (한글)
        authority: 현재 권한 (한글)
        driving_state: 주행 상태 (한글)
        emergency_sources: 활성화된 비상정지 원인 리스트
        emergency_complete: 비상정지 처리 완료 여부
    """
    device_bits: int
    devices: dict[str, bool]
    operation_mode_raw: int
    operation_mode: str
    authority_raw: int
    authority: str
    driving_state_raw: int
    driving_state: str
    emergency_bits: int
    emergency_sources: list[str]
    emergency_complete: bool

    def to_dict(self) -> dict:
        return {
            "devices": self.devices,
            "operation_mode": self.operation_mode,
            "authority": self.authority,
            "driving_state": self.driving_state,
            "emergency_sources": self.emergency_sources,
            "emergency_complete": self.emergency_complete,
        }

    @property
    def is_emergency(self) -> bool:
        """비상정지 상태 여부."""
        return len(self.emergency_sources) > 0

    def get_emergency_reasons(self) -> list[str]:
        """비상정지 원인 리스트."""
        return self.emergency_sources

    def get_emergency_dict(self) -> dict[str, bool]:
        """UI용 비상정지 상태 딕셔너리."""
        result = {src: (src in self.emergency_sources) for src in EMERGENCY_SOURCE_NAMES}
        result["처리완료"] = self.emergency_complete
        return result


@dataclass
class ParseResult:
    """ICD 파싱 결과.

    Attributes:
        success: 파싱 성공 여부
        header: 파싱된 헤더 (실패 시 None)
        raw_payload: 원본 페이로드 바이트
        payload: 파싱된 페이로드 객체 (0x01만 지원)
        checksum_ok: 체크섬 검증 결과
        error: 에러 메시지 (실패 시)
        raw_size: 전체 패킷 크기
    """
    success: bool
    header: Optional[ICDHeader] = None
    raw_payload: Optional[bytes] = None
    payload: Optional[OperationalPayload] = None
    checksum_ok: bool = False
    error: Optional[str] = None
    raw_size: int = 0

    def to_dict(self) -> dict:
        result = {"success": self.success, "checksum_ok": self.checksum_ok, "raw_size": self.raw_size}
        if self.header:
            result["header"] = self.header.to_dict()
        if self.raw_payload:
            result["raw_payload_size"] = len(self.raw_payload)
        if self.payload:
            result["payload"] = self.payload.to_dict()
        if self.error:
            result["error"] = self.error
        return result
