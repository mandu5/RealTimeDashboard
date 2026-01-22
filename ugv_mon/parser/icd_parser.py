"""
ICD v1.0 Parser - 패킷 헤더 및 페이로드 파싱.
"""

import struct
import logging
from typing import Dict, TypeVar, Type, Union
from enum import IntEnum

from .models import ICDHeader, StatusPayload, ParseResult, MsgCode, AckFlag, DeviceID

logger = logging.getLogger(__name__)

# 헬퍼 함수
T = TypeVar('T', bound=IntEnum)

def safe_enum(enum_class: Type[T], value: int) -> Union[T, int]:
   
    try:
        return enum_class(value)
    except ValueError:
        return value
class ICDParser:
    """ICD v1.0 패킷 파서."""

    HEADER_SIZE = 12
    CHECKSUM_SIZE = 2
    MIN_PACKET_SIZE = 14
    MSG_CODE_STATUS_REPORT = 0x01

    # 운용 모드 라벨 (bits 7-5)
    OPERATION_MODE_LABELS = {
        0b000: "준비 (PREP)",
        0b001: "전환 중 (TRANSITION)",
        0b010: "무인 주행 (UNMANNED DRIVING)",
        0b011: "무인 사격 (UNMANNED FIRING)",
        0b100: "비상 정지 (EMERGENCY STOP)",
    }

    # 운용 권한 라벨 (bits 3-2)
    AUTHORITY_LABELS = {
        0b00: "해제됨 (RELEASED)",
        0b01: "OCS 획득 (OCS ACQUIRED)",
        0b10: "근거리조종기 (NEAR CONTROLLER)",
    }

    # 주행 상태 라벨 (bits 1-0)
    DRIVING_STATE_LABELS = {
        0b01: "원격 (REMOTE)",
        0b10: "종속주행 (PLATOONING)",
        0b11: "자율배치 (AUTONOMOUS DISPATCH)",
    }

    # 장치 이름 (bit 0~9)
    DEVICE_NAMES = ["VIC", "RDC", "ADC", "FCAM", "RCAM", "ACAM", "SCS", "DIP", "TCC", "TM"]

    # 비상정지 원인 (bit 6~15)
    EMERGENCY_NAMES = [
        "통신 두절", "장비고장(주행)", "장비고장(동력계)",
        "신호단절(주행)", "신호단절(자율)", "신호단절(항법)",
        "신호단절(동력계)", "신호단절(통신)",
        "수동정지(운용통제장치)", "수동정지(근거리조종기)",
    ]

    def __init__(self):
        self._parse_count = 0
        self._success_count = 0
        self._checksum_fail_count = 0

    def parse(self, data: bytes) -> ParseResult:
        """패킷 파싱."""
        self._parse_count += 1

        # 최소 길이 검증
        if len(data) < self.MIN_PACKET_SIZE:
            return ParseResult(
                success=False,
                error=f"Packet too short: {len(data)} < {self.MIN_PACKET_SIZE}",
                raw_size=len(data)
            )

        # 체크섬 검증
        checksum_ok = self._verify_checksum(data)
        if not checksum_ok:
            self._checksum_fail_count += 1

        # 헤더 파싱
        try:
            header = self._parse_header(data)
        except Exception as e:
            return ParseResult(
                success=False,
                checksum_ok=checksum_ok,
                error=f"Header parsing failed: {e}",
                raw_size=len(data)
            )

        # 페이로드 파싱 (상태보고)
        payload = None
        if header.msg_code == self.MSG_CODE_STATUS_REPORT:
            payload_data = data[self.HEADER_SIZE:-self.CHECKSUM_SIZE]
            try:
                payload = self._parse_status_payload(payload_data)
            except Exception as e:
                logger.warning(f"Payload parsing failed: {e}")

        self._success_count += 1
        return ParseResult(
            success=True,
            header=header,
            payload=payload,
            checksum_ok=checksum_ok,
            raw_size=len(data)
        )

    def _verify_checksum(self, data: bytes) -> bool:
        """체크섬 검증."""
        if len(data) < self.CHECKSUM_SIZE:
            return False
        data_without_checksum = data[:-self.CHECKSUM_SIZE]
        received = struct.unpack('<H', data[-self.CHECKSUM_SIZE:])[0]
        calculated = sum(data_without_checksum) & 0xFFFF
        return calculated == received

    def _parse_header(self, data: bytes) -> ICDHeader:
        """헤더 파싱 (12 bytes)."""
        if len(data) < 12:
            raise ValueError(f"헤더 길이 부족: {len(data)} < 12")
    
        return ICDHeader(
            timestamp=struct.unpack('<I', data[0:4])[0],
            sequence=data[3],                              # timestamp 마지막 1바이트
            source_id=safe_enum(DeviceID, data[4]),
            dest_id=safe_enum(DeviceID, data[5]),
            msg_code=safe_enum(MsgCode, data[6]),
            ack_flag=safe_enum(AckFlag, data[7]),
            reserved=struct.unpack('<H', data[8:10])[0],
            data_length=struct.unpack('<H', data[10:12])[0],
        )

    def _parse_status_payload(self, payload: bytes) -> StatusPayload:
        """상태보고 페이로드 파싱."""
        # 장치 연결 상태
        device_presence = struct.unpack('<H', payload[0:2])[0]
        devices = {
            name: bool(device_presence & (1 << i))
            for i, name in enumerate(self.DEVICE_NAMES)
        }

        # VIC 운용 상태
        vic_state = payload[2]
        operation_mode = (vic_state >> 5) & 0x07
        authority = (vic_state >> 2) & 0x03
        driving_state = vic_state & 0x03

        # 비상정지 원인
        emergency_word = struct.unpack('<H', payload[3:5])[0]
        emergency_bits = (emergency_word >> 6) & 0x3FF
        emergency_status = {
            name: bool(emergency_bits & (1 << i))
            for i, name in enumerate(self.EMERGENCY_NAMES)
        }

        return StatusPayload(
            device_presence=device_presence,
            devices=devices,
            vic_state_byte=vic_state,
            operation_mode=operation_mode,
            operation_mode_label=self.OPERATION_MODE_LABELS.get(operation_mode, f"알 수 없음 ({operation_mode})"),
            authority=authority,
            authority_label=self.AUTHORITY_LABELS.get(authority, f"알 수 없음 ({authority})"),
            driving_state=driving_state,
            driving_state_label=self.DRIVING_STATE_LABELS.get(driving_state, f"알 수 없음 ({driving_state})"),
            emergency_word=emergency_word,
            emergency_status=emergency_status
        )

    def get_stats(self) -> Dict:
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
