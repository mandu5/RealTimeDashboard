"""
ICD v1.0 Parser - 헤더 및 페이로드 파싱.

5주차: 0x01 운용 상태 페이로드 파싱 추가.
"""

import struct
import logging
from typing import TypeVar, Type, Union, Optional

from enum import IntEnum

from ..core import (
    ICDHeader, ParseResult, MsgCode, AckFlag, DeviceID,
    OperationalPayload, OPERATION_MODES, AUTHORITIES, DRIVING_STATES,
    DEVICE_BIT_NAMES, EMERGENCY_SOURCE_NAMES,
)
from ..core.constants import ICD_HEADER_SIZE, ICD_CHECKSUM_SIZE, ICD_MIN_PACKET_SIZE

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=IntEnum)


def safe_enum(enum_class: Type[T], value: int) -> Union[T, int]:
    """안전한 enum 변환 (알 수 없는 값은 int로 반환)."""
    try:
        return enum_class(value)
    except ValueError:
        return value


class ICDParser:
    """ICD v1.0 패킷 파서."""

    # 운용 상태 페이로드가 있는 msg_code와 예상 data_length
    OPERATIONAL_MSG_CODE = 0x01
    OPERATIONAL_DATA_LENGTH = 87

    def __init__(self):
        self._parse_count = 0
        self._success_count = 0
        self._checksum_fail_count = 0
        self._payload_success_count = 0

    def parse(self, data: bytes) -> ParseResult:
        """패킷 파싱 (헤더 + 페이로드)."""
        self._parse_count += 1

        # 최소 길이 검증
        if len(data) < ICD_MIN_PACKET_SIZE:
            return ParseResult(success=False, error=f"Packet too short: {len(data)} < {ICD_MIN_PACKET_SIZE}", raw_size=len(data))

        # 체크섬 검증
        checksum_ok = self._verify_checksum(data)
        if not checksum_ok:
            self._checksum_fail_count += 1

        # 헤더 파싱
        try:
            header = self._parse_header(data)
        except Exception as e:
            logger.warning(f"Header parsing failed: {e}")
            return ParseResult(success=False, checksum_ok=checksum_ok, error=f"Header parsing failed: {e}", raw_size=len(data))

        # 페이로드 추출
        raw_payload = data[ICD_HEADER_SIZE:-ICD_CHECKSUM_SIZE] if len(data) > ICD_MIN_PACKET_SIZE else None
        
        # 운용 상태 페이로드 파싱 시도 (0x01, data_length=87)
        payload = None
        msg_code_value = header.msg_code if isinstance(header.msg_code, int) else header.msg_code.value
        
        if (msg_code_value == self.OPERATIONAL_MSG_CODE and 
            header.data_length == self.OPERATIONAL_DATA_LENGTH and 
            raw_payload and len(raw_payload) >= 5):
            try:
                payload = self._parse_operational_payload(raw_payload)
                self._payload_success_count += 1
            except Exception as e:
                logger.debug(f"Operational payload parsing failed: {e}")

        self._success_count += 1
        return ParseResult(
            success=True, 
            header=header, 
            raw_payload=raw_payload, 
            payload=payload,
            checksum_ok=checksum_ok, 
            raw_size=len(data)
        )

    def _verify_checksum(self, data: bytes) -> bool:
        """체크섬 검증."""
        if len(data) < ICD_CHECKSUM_SIZE:
            return False
        received = struct.unpack('<H', data[-ICD_CHECKSUM_SIZE:])[0]
        calculated = sum(data[:-ICD_CHECKSUM_SIZE]) & 0xFFFF
        return calculated == received

    def _parse_header(self, data: bytes) -> ICDHeader:
        """헤더 파싱 (12 bytes)."""
        if len(data) < ICD_HEADER_SIZE:
            raise ValueError(f"헤더 길이 부족: {len(data)} < {ICD_HEADER_SIZE}")
    
        return ICDHeader(
            timestamp=struct.unpack('<I', data[0:4])[0],
            sequence=data[3] & 0x0F,  # 하위 4비트만 사용 (0~15 반복)
            source_id=safe_enum(DeviceID, data[4]),
            dest_id=safe_enum(DeviceID, data[5]),
            msg_code=safe_enum(MsgCode, data[6]),
            ack_flag=safe_enum(AckFlag, data[7]),
            reserved=struct.unpack('<H', data[8:10])[0],
            data_length=struct.unpack('<H', data[10:12])[0],
        )

    def _parse_operational_payload(self, payload: bytes) -> OperationalPayload:
        """운용 상태 페이로드 파싱 (5 bytes 필수, 총 87 bytes)."""
        if len(payload) < 5:
            raise ValueError(f"페이로드 길이 부족: {len(payload)} < 5")
        
        # 1~2 바이트: 장치 연결 목록 (Bit 9~0)
        device_bits = struct.unpack('<H', payload[0:2])[0]
        devices = {
            name: bool(device_bits & (1 << i))
            for i, name in enumerate(DEVICE_BIT_NAMES)
        }
        
        # 3 바이트: 운용 상태
        status_byte = payload[2]
        operation_mode_raw = (status_byte >> 5) & 0x07  # Bit 7~5
        authority_raw = (status_byte >> 2) & 0x03       # Bit 3~2
        driving_state_raw = status_byte & 0x03          # Bit 1~0
        
        operation_mode = OPERATION_MODES.get(operation_mode_raw, f"Unknown({operation_mode_raw})")
        authority = AUTHORITIES.get(authority_raw, f"Unknown({authority_raw})")
        driving_state = DRIVING_STATES.get(driving_state_raw, f"Unknown({driving_state_raw})")
        
        # 4~5 바이트: 비상정지
        emergency_bits = struct.unpack('<H', payload[3:5])[0]
        emergency_sources_raw = (emergency_bits >> 6) & 0x3FF  # Bit 15~6
        emergency_complete = bool(emergency_bits & 0x01)       # Bit 0
        
        emergency_sources = [
            EMERGENCY_SOURCE_NAMES[i] 
            for i in range(len(EMERGENCY_SOURCE_NAMES)) 
            if (emergency_sources_raw >> i) & 1
        ]
        if not emergency_sources:
            emergency_sources = ["없음"]
        
        return OperationalPayload(
            device_bits=device_bits,
            devices=devices,
            operation_mode_raw=operation_mode_raw,
            operation_mode=operation_mode,
            authority_raw=authority_raw,
            authority=authority,
            driving_state_raw=driving_state_raw,
            driving_state=driving_state,
            emergency_bits=emergency_bits,
            emergency_sources=emergency_sources,
            emergency_complete=emergency_complete,
        )

    def get_stats(self) -> dict:
        """파싱 통계."""
        return {
            "parse_count": self._parse_count,
            "success_count": self._success_count,
            "checksum_fail_count": self._checksum_fail_count,
            "payload_success_count": self._payload_success_count,
            "success_rate": self._success_count / self._parse_count * 100 if self._parse_count > 0 else 100.0,
        }

    def reset_stats(self) -> None:
        """통계 초기화."""
        self._parse_count = 0
        self._success_count = 0
        self._checksum_fail_count = 0
        self._payload_success_count = 0
