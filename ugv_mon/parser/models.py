"""
ICD Parser 데이터 모델.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Union
from enum import IntEnum


class MsgCode(IntEnum):
    """메시지 코드.
    
    NOTE: ICD 명세 확정 전까지 각 코드의 의미는 미확정.
    명세 확정 시 의미 있는 이름으로 변경 예정.
    """
    TYPE_01 = 0x01  # 운용 상태 메시지 (50000→61000, data_length=87)
    REMOTE_CONTROL = 0x10  # 원격 제어 메시지 (61000→50000, 80~110Hz)
    TYPE_25 = 0x25  # Heartbeat
    TYPE_40 = 0x40


class AckFlag(IntEnum):
    """ACK 플래그."""
    REQUESTED = 0x00
    NOT_REQUESTED = 0xFF


class DeviceID(IntEnum):
    """장치 ID."""
    VIC = 0xB1   # 177 - 송신측 50000
    OCS = 0xA2   # 162 - 수신측 61000


@dataclass
class ICDHeader:
    """ICD v1.0 헤더 (12 bytes)."""
    timestamp: int
    sequence: int
    source_id: Union[DeviceID, int]
    dest_id: Union[DeviceID, int]
    msg_code: Union[MsgCode, int]
    ack_flag: Union[AckFlag, int]
    reserved: int
    data_length: int

    def to_dict(self) -> Dict:
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
class ParseResult:
    """
    파싱 결과.
    
    - success: 헤더 파싱 성공 여부
    - header: 파싱된 ICD 헤더
    - raw_payload: 원본 페이로드
    - payload: 파싱된 페이로드 (0x01 운용 상태 등)
    """
    success: bool
    header: Optional[ICDHeader] = None
    raw_payload: Optional[bytes] = None
    payload: Optional["OperationalPayload"] = None  # 5주차: 추가
    checksum_ok: bool = False
    error: Optional[str] = None
    raw_size: int = 0

    def to_dict(self) -> Dict:
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


# =============================================================================
# 운용 상태 페이로드 (0x01, data_length=87)
# =============================================================================

# 운용 모드 매핑
OPERATION_MODES = {0: "준비", 1: "무인주행", 2: "유인주행", 3: "비상정지", 4: "점검", 5: "원격"}

# 운용 권한 매핑
AUTHORITIES = {0: "없음", 1: "OCS(운용통제기)", 2: "근거리조종기", 3: "VIC"}

# 주행 상태 매핑
DRIVING_STATES = {0: "정지", 1: "전진", 2: "후진", 3: "회전"}

# 장치 이름 매핑 (Bit 순서)
DEVICE_BIT_NAMES = ["VIC", "RDC", "ADC", "FCAM", "RCAM", "ACAM", "SCS", "DIP", "TCC", "TM"]

# 비상정지 원인 매핑 (Bit 순서)
EMERGENCY_SOURCE_NAMES = ["미식별", "운전자", "원격", "장애물", "경사", "속도초과", "통신이상", "배터리", "엔진", "기타"]


@dataclass
class OperationalPayload:
    """운용 상태 페이로드 (0x01, 87 bytes)."""
    
    # 장치 연결 상태 (Bit 9~0)
    device_bits: int
    devices: Dict[str, bool]
    
    # 운용 상태 (1 byte)
    operation_mode_raw: int
    operation_mode: str
    authority_raw: int
    authority: str
    driving_state_raw: int
    driving_state: str
    
    # 비상정지 상태 (2 bytes)
    emergency_bits: int
    emergency_sources: list
    emergency_complete: bool
    
    def to_dict(self) -> Dict:
        return {
            "devices": self.devices,
            "operation_mode": self.operation_mode,
            "authority": self.authority,
            "driving_state": self.driving_state,
            "emergency_sources": self.emergency_sources,
            "emergency_complete": self.emergency_complete,
        }

