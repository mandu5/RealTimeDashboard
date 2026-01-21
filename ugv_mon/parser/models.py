"""
ICD Parser 데이터 모델.
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class ICDHeader:
    """ICD v1.0 헤더 (12 bytes)."""
    timestamp: int
    sequence: int
    source_id: int
    dest_id: int
    msg_code: int
    ack_flag: int
    reserved: int
    data_length: int

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "source_id": f"0x{self.source_id:02X}",
            "dest_id": f"0x{self.dest_id:02X}",
            "msg_code": f"0x{self.msg_code:02X}",
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
