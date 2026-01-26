"""
ICD v1.0 Parser - 헤더 파싱 전용.

NOTE: 페이로드는 ICD 명세 확정 전까지 raw_payload로 저장.
명세 확정 시 msg_code별 파싱 로직 추가 예정.
"""

import struct
import logging
from typing import TypeVar, Type, Union
from enum import IntEnum

from .models import ICDHeader, ParseResult, MsgCode, AckFlag, DeviceID
from ..constants import ICD_HEADER_SIZE, ICD_CHECKSUM_SIZE, ICD_MIN_PACKET_SIZE

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=IntEnum)


def safe_enum(enum_class: Type[T], value: int) -> Union[T, int]:
    """안전한 enum 변환 (알 수 없는 값은 int로 반환)."""
    try:
        return enum_class(value)
    except ValueError:
        return value


class ICDParser:
    """ICD v1.0 패킷 파서 (헤더 전용)."""

    def __init__(self):
        self._parse_count = 0
        self._success_count = 0
        self._checksum_fail_count = 0

    def parse(self, data: bytes) -> ParseResult:
        """패킷 파싱 (헤더 + raw_payload)."""
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

        # 페이로드 추출 (파싱 없이 raw 저장)
        raw_payload = data[ICD_HEADER_SIZE:-ICD_CHECKSUM_SIZE] if len(data) > ICD_MIN_PACKET_SIZE else None

        self._success_count += 1
        return ParseResult(success=True, header=header, raw_payload=raw_payload, checksum_ok=checksum_ok, raw_size=len(data))

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
            sequence=data[3],
            source_id=safe_enum(DeviceID, data[4]),
            dest_id=safe_enum(DeviceID, data[5]),
            msg_code=safe_enum(MsgCode, data[6]),
            ack_flag=safe_enum(AckFlag, data[7]),
            reserved=struct.unpack('<H', data[8:10])[0],
            data_length=struct.unpack('<H', data[10:12])[0],
        )

    def get_stats(self) -> dict:
        """파싱 통계."""
        return {
            "parse_count": self._parse_count,
            "success_count": self._success_count,
            "checksum_fail_count": self._checksum_fail_count,
            "success_rate": self._success_count / self._parse_count * 100 if self._parse_count > 0 else 100.0,
        }

    def reset_stats(self) -> None:
        """통계 초기화."""
        self._parse_count = 0
        self._success_count = 0
        self._checksum_fail_count = 0
