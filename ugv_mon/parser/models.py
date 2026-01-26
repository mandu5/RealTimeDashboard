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
    TYPE_01 = 0x01
    TYPE_25 = 0x25
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
    - raw_payload: 원본 페이로드 (ICD 명세 확정 후 파싱 예정)
    """
    success: bool
    header: Optional[ICDHeader] = None
    raw_payload: Optional[bytes] = None
    checksum_ok: bool = False
    error: Optional[str] = None
    raw_size: int = 0

    def to_dict(self) -> Dict:
        result = {"success": self.success, "checksum_ok": self.checksum_ok, "raw_size": self.raw_size}
        if self.header:
            result["header"] = self.header.to_dict()
        if self.raw_payload:
            result["raw_payload_size"] = len(self.raw_payload)
        if self.error:
            result["error"] = self.error
        return result


# =============================================================================
# StatusPayload는 ICD 명세 확정 후 추가 예정
# 현재는 페이로드 파싱하지 않음
# =============================================================================
