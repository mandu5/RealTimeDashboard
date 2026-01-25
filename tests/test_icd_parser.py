"""
ICD Parser 단위 테스트.

테스트 실행:
    python -m pytest tests/test_icd_parser.py -v
"""

import struct
import pytest
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ugv_mon.parser.icd_parser import ICDParser
from ugv_mon.parser.models import ParseResult, MsgCode, DeviceID, AckFlag
from ugv_mon.constants import ICD_HEADER_SIZE, ICD_CHECKSUM_SIZE, ICD_MIN_PACKET_SIZE


class TestICDParserBasic:
    """기본 파싱 테스트."""

    def setup_method(self):
        """각 테스트 전 파서 초기화."""
        self.parser = ICDParser()

    def test_packet_too_short(self):
        """최소 길이 미만 패킷 거부."""
        short_data = b'\x00' * (ICD_MIN_PACKET_SIZE - 1)
        result = self.parser.parse(short_data)
        
        assert result.success is False
        assert "too short" in result.error.lower()
        assert result.raw_size == len(short_data)

    def test_minimum_length_packet(self):
        """최소 길이 패킷 파싱."""
        # 12바이트 헤더 + 2바이트 체크섬 = 14바이트
        header = bytes([
            0x01, 0x02, 0x03, 0x04,  # timestamp (seq=0x04)
            0xB1,                     # source_id (VIC)
            0xA2,                     # dest_id (OCS)
            0x01,                     # msg_code (STATUS_REPORT)
            0xFF,                     # ack_flag
            0x00, 0x00,              # reserved
            0x00, 0x00,              # data_length = 0
        ])
        checksum = sum(header) & 0xFFFF
        packet = header + struct.pack('<H', checksum)
        
        result = self.parser.parse(packet)
        
        assert result.success is True
        assert result.checksum_ok is True
        assert result.header is not None
        assert result.header.sequence == 0x04

    def test_checksum_verification_pass(self):
        """올바른 체크섬 검증."""
        header = bytes([0x10, 0x20, 0x30, 0x40, 0xB1, 0xA2, 0x01, 0xFF, 0x00, 0x00, 0x00, 0x00])
        checksum = sum(header) & 0xFFFF
        packet = header + struct.pack('<H', checksum)
        
        result = self.parser.parse(packet)
        
        assert result.checksum_ok is True

    def test_checksum_verification_fail(self):
        """잘못된 체크섬 거부."""
        header = bytes([0x10, 0x20, 0x30, 0x40, 0xB1, 0xA2, 0x01, 0xFF, 0x00, 0x00, 0x00, 0x00])
        wrong_checksum = struct.pack('<H', 0xFFFF)  # 잘못된 체크섬
        packet = header + wrong_checksum
        
        result = self.parser.parse(packet)
        
        assert result.checksum_ok is False


class TestICDParserHeader:
    """헤더 파싱 테스트."""

    def setup_method(self):
        self.parser = ICDParser()

    def _create_packet(self, header_bytes: bytes, payload: bytes = b'') -> bytes:
        """패킷 생성 헬퍼."""
        data = header_bytes + payload
        checksum = sum(data) & 0xFFFF
        return data + struct.pack('<H', checksum)

    def test_parse_timestamp(self):
        """타임스탬프 파싱."""
        # Timestamp = 0x04030201 (Little Endian)
        header = bytes([
            0x01, 0x02, 0x03, 0x04,  # timestamp
            0xB1, 0xA2, 0x01, 0xFF,
            0x00, 0x00, 0x00, 0x00,
        ])
        packet = self._create_packet(header)
        
        result = self.parser.parse(packet)
        
        assert result.header.timestamp == 0x04030201

    def test_parse_sequence_from_timestamp(self):
        """시퀀스 번호 파싱 (timestamp 마지막 바이트)."""
        header = bytes([
            0x00, 0x00, 0x00, 0x7F,  # seq = 0x7F = 127
            0xB1, 0xA2, 0x01, 0xFF,
            0x00, 0x00, 0x00, 0x00,
        ])
        packet = self._create_packet(header)
        
        result = self.parser.parse(packet)
        
        assert result.header.sequence == 127

    def test_parse_source_dest_ids(self):
        """소스/목적지 ID 파싱."""
        header = bytes([
            0x00, 0x00, 0x00, 0x00,
            0xB1,  # VIC
            0xA2,  # OCS
            0x01, 0xFF,
            0x00, 0x00, 0x00, 0x00,
        ])
        packet = self._create_packet(header)
        
        result = self.parser.parse(packet)
        
        assert result.header.source_id == DeviceID.VIC
        assert result.header.dest_id == DeviceID.OCS

    def test_parse_unknown_device_id(self):
        """알 수 없는 장치 ID 처리."""
        header = bytes([
            0x00, 0x00, 0x00, 0x00,
            0x99,  # Unknown
            0x88,  # Unknown
            0x01, 0xFF,
            0x00, 0x00, 0x00, 0x00,
        ])
        packet = self._create_packet(header)
        
        result = self.parser.parse(packet)
        
        # Unknown ID는 int로 저장됨
        assert result.header.source_id == 0x99
        assert result.header.dest_id == 0x88

    def test_parse_data_length(self):
        """데이터 길이 파싱."""
        header = bytes([
            0x00, 0x00, 0x00, 0x00,
            0xB1, 0xA2, 0x01, 0xFF,
            0x00, 0x00,
            0x57, 0x00,  # data_length = 0x0057 = 87
        ])
        packet = self._create_packet(header)
        
        result = self.parser.parse(packet)
        
        assert result.header.data_length == 87


class TestICDParserPayload:
    """페이로드 파싱 테스트."""

    def setup_method(self):
        self.parser = ICDParser()

    def _create_status_packet(self, payload: bytes) -> bytes:
        """상태보고 패킷 생성."""
        header = bytes([
            0x00, 0x00, 0x00, 0x01,  # seq = 1
            0xB1, 0xA2,              # VIC -> OCS
            0x01,                    # msg_code = STATUS_REPORT
            0xFF,
            0x00, 0x00,
            len(payload) & 0xFF, (len(payload) >> 8) & 0xFF,
        ])
        data = header + payload
        checksum = sum(data) & 0xFFFF
        return data + struct.pack('<H', checksum)

    def test_parse_device_presence(self):
        """장치 연결 상태 파싱."""
        # bit0=VIC, bit1=RDC connected = 0b00000011 = 0x03
        payload = bytes([
            0x03, 0x00,  # device_presence
            0x00,        # vic_state
            0x00, 0x00,  # emergency
        ])
        packet = self._create_status_packet(payload)
        
        result = self.parser.parse(packet)
        
        assert result.payload is not None
        assert result.payload.devices["VIC"] is True
        assert result.payload.devices["RDC"] is True
        assert result.payload.devices["ADC"] is False

    def test_parse_operation_mode(self):
        """운용 모드 파싱."""
        # bits 7-5 = 010 = 무인주행
        vic_state = 0b01000000  # 0x40
        payload = bytes([
            0xFF, 0x03,  # device_presence
            vic_state,
            0x00, 0x00,
        ])
        packet = self._create_status_packet(payload)
        
        result = self.parser.parse(packet)
        
        assert result.payload.operation_mode == 0b010
        assert "무인 주행" in result.payload.operation_mode_label

    def test_parse_authority(self):
        """운용 권한 파싱."""
        # bits 3-2 = 01 = OCS 획득
        vic_state = 0b00000100  # 0x04
        payload = bytes([
            0xFF, 0x03,
            vic_state,
            0x00, 0x00,
        ])
        packet = self._create_status_packet(payload)
        
        result = self.parser.parse(packet)
        
        assert result.payload.authority == 0b01
        assert "OCS" in result.payload.authority_label

    def test_parse_emergency_status(self):
        """비상정지 원인 파싱."""
        # bit6 = 통신 두절 → emergency_word = 0b0000000001000000 = 0x0040
        payload = bytes([
            0xFF, 0x03,
            0x00,
            0x40, 0x00,  # emergency_word
        ])
        packet = self._create_status_packet(payload)
        
        result = self.parser.parse(packet)
        
        assert result.payload.emergency_status["통신 두절"] is True
        assert result.payload.emergency_status["장비고장(주행)"] is False


class TestICDParserStats:
    """파싱 통계 테스트."""

    def setup_method(self):
        self.parser = ICDParser()

    def test_stats_initial(self):
        """초기 통계."""
        stats = self.parser.get_stats()
        
        assert stats["parse_count"] == 0
        assert stats["success_count"] == 0
        assert stats["checksum_fail_count"] == 0

    def test_stats_after_success(self):
        """성공 후 통계."""
        header = bytes([0] * 12)
        checksum = struct.pack('<H', sum(header) & 0xFFFF)
        packet = header + checksum
        
        self.parser.parse(packet)
        stats = self.parser.get_stats()
        
        assert stats["parse_count"] == 1
        assert stats["success_count"] == 1

    def test_stats_reset(self):
        """통계 초기화."""
        header = bytes([0] * 12)
        checksum = struct.pack('<H', sum(header) & 0xFFFF)
        packet = header + checksum
        
        self.parser.parse(packet)
        self.parser.reset_stats()
        stats = self.parser.get_stats()
        
        assert stats["parse_count"] == 0
        assert stats["success_count"] == 0
