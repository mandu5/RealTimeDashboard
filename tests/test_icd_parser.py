"""
ICD Parser 단위 테스트.

테스트 실행:
    python -m pytest tests/test_icd_parser.py -v
    
NOTE: 페이로드 테스트는 ICD 명세 확정 후 추가 예정.
현재는 헤더 파싱만 테스트합니다.
"""

import struct
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ugv_mon.parser.icd_parser import ICDParser
from ugv_mon.parser.models import ParseResult, MsgCode, DeviceID, AckFlag
from ugv_mon.constants import ICD_HEADER_SIZE, ICD_CHECKSUM_SIZE, ICD_MIN_PACKET_SIZE


class TestICDParserBasic:
    """기본 파싱 테스트."""

    def setup_method(self):
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
        header = bytes([
            0x01, 0x02, 0x03, 0x04,  # timestamp (seq=0x04)
            0xB1, 0xA2,              # VIC -> OCS
            0x01, 0xFF,              # msg_code, ack
            0x00, 0x00, 0x00, 0x00,  # reserved, data_length
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
        wrong_checksum = struct.pack('<H', 0xFFFF)
        packet = header + wrong_checksum
        
        result = self.parser.parse(packet)
        
        assert result.checksum_ok is False


class TestICDParserHeader:
    """헤더 파싱 테스트."""

    def setup_method(self):
        self.parser = ICDParser()

    def _create_packet(self, header_bytes: bytes, payload: bytes = b'') -> bytes:
        data = header_bytes + payload
        checksum = sum(data) & 0xFFFF
        return data + struct.pack('<H', checksum)

    def test_parse_timestamp(self):
        """타임스탬프 파싱."""
        header = bytes([0x01, 0x02, 0x03, 0x04, 0xB1, 0xA2, 0x01, 0xFF, 0x00, 0x00, 0x00, 0x00])
        packet = self._create_packet(header)
        
        result = self.parser.parse(packet)
        
        assert result.header.timestamp == 0x04030201

    def test_parse_sequence_from_timestamp(self):
        """시퀀스 번호 파싱 (4비트: 0~15)."""
        header = bytes([0x00, 0x00, 0x00, 0x7F, 0xB1, 0xA2, 0x01, 0xFF, 0x00, 0x00, 0x00, 0x00])
        packet = self._create_packet(header)
        
        result = self.parser.parse(packet)
        
        # 0x7F & 0x0F = 15 (하위 4비트만 사용)
        assert result.header.sequence == 15

    def test_parse_source_dest_ids(self):
        """소스/목적지 ID 파싱."""
        header = bytes([0x00, 0x00, 0x00, 0x00, 0xB1, 0xA2, 0x01, 0xFF, 0x00, 0x00, 0x00, 0x00])
        packet = self._create_packet(header)
        
        result = self.parser.parse(packet)
        
        assert result.header.source_id == DeviceID.VIC
        assert result.header.dest_id == DeviceID.OCS

    def test_parse_unknown_device_id(self):
        """알 수 없는 장치 ID 처리."""
        header = bytes([0x00, 0x00, 0x00, 0x00, 0x99, 0x88, 0x01, 0xFF, 0x00, 0x00, 0x00, 0x00])
        packet = self._create_packet(header)
        
        result = self.parser.parse(packet)
        
        assert result.header.source_id == 0x99
        assert result.header.dest_id == 0x88

    def test_parse_data_length(self):
        """데이터 길이 파싱."""
        header = bytes([0x00, 0x00, 0x00, 0x00, 0xB1, 0xA2, 0x01, 0xFF, 0x00, 0x00, 0x57, 0x00])
        packet = self._create_packet(header)
        
        result = self.parser.parse(packet)
        
        assert result.header.data_length == 87

    def test_raw_payload_stored(self):
        """페이로드가 raw로 저장되는지 확인."""
        header = bytes([0x00, 0x00, 0x00, 0x01, 0xB1, 0xA2, 0x01, 0xFF, 0x00, 0x00, 0x05, 0x00])
        payload = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE])
        packet = self._create_packet(header, payload)
        
        result = self.parser.parse(packet)
        
        assert result.success is True
        assert result.raw_payload == payload


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


# =============================================================================
# TestICDParserPayload - ICD 명세 확정 후 추가 예정
# =============================================================================
