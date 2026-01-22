"""
ICD Parser 데이터 모델.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Union
from enum import IntEnum

class MsgCode(IntEnum):
    """메시지 코드 (송신 메시지 타입)."""
    TYPE_01 = 0x01        # 1 - 정확한 의미는 멘토님 확인
    TYPE_25 = 0x25        # 37 - 정확한 의미는 멘토님 확인
    TYPE_40 = 0x40  # 64 정확한 의미는 멘토님 확인


class AckFlag(IntEnum):
    """ACK 플래그."""
    REQUESTED = 0x00      # ACK 요청
    NOT_REQUESTED = 0xFF  # ACK 미요청


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
        # source_id 포맷
        if isinstance(self.source_id, DeviceID):
            source_str = f"{self.source_id.name} (0x{self.source_id:02X})"
        else:
            source_str = f"UNKNOWN (0x{self.source_id:02X})"
        
        # dest_id 포맷
        if isinstance(self.dest_id, DeviceID):
            dest_str = f"{self.dest_id.name} (0x{self.dest_id:02X})"
        else:
            dest_str = f"UNKNOWN (0x{self.dest_id:02X})"
        
        # msg_code 포맷
        if isinstance(self.msg_code, MsgCode):
            msg_str = f"{self.msg_code.name} (0x{self.msg_code:02X})"
        else:
            msg_str = f"UNKNOWN (0x{self.msg_code:02X})"
        
        # ack_flag 포맷
        if isinstance(self.ack_flag, AckFlag):
            ack_str = f"{self.ack_flag.name} (0x{self.ack_flag:02X})"
        else:
            ack_str = f"UNKNOWN (0x{self.ack_flag:02X})"
        
        return {
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "source_id": source_str,
            "dest_id": dest_str,
            "msg_code": msg_str,
            "ack_flag": ack_str,
            "data_length": self.data_length,
        }


@dataclass
class StatusPayload:
    """상태보고 페이로드 (MSG Code = 0x01)."""
    device_presence: int
    devices: Dict[str, bool]
    vic_state_byte: int
    operation_mode: int
    operation_mode_label: str
    authority: int
    authority_label: str
    driving_state: int
    driving_state_label: str
    emergency_word: int
    emergency_status: Dict[str, bool]

    def to_dict(self) -> Dict:
        return {
            "devices": self.devices,
            "operation_mode": self.operation_mode_label,
            "authority": self.authority_label,
            "driving_state": self.driving_state_label,
            "emergency_status": self.emergency_status,
        }


@dataclass
class ParseResult:
    """파싱 결과."""
    success: bool
    header: Optional[ICDHeader] = None
    payload: Optional[StatusPayload] = None
    checksum_ok: bool = False
    error: Optional[str] = None
    raw_size: int = 0

    @property
    def is_status_report(self) -> bool:
        return self.success and self.header is not None and self.header.msg_code == 0x01

    def to_dict(self) -> Dict:
        result = {"success": self.success, "checksum_ok": self.checksum_ok, "raw_size": self.raw_size}
        if self.header:
            result["header"] = self.header.to_dict()
        if self.payload:
            result["payload"] = self.payload.to_dict()
        if self.error:
            result["error"] = self.error
        return result
