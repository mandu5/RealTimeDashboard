"""
ICD v1.0 Parser Implementation.

ICD v1.0 규격에 따라 패킷을 파싱하는 메인 클래스입니다.

=============================================================================
파싱 플로우:
1. 최소 길이 검증 (14 bytes = 헤더 12 + 체크섬 2)
2. 체크섬 검증 (모든 바이트 합 & 0xFFFF)
3. 헤더 파싱 (12 bytes)
4. 길이 검증 (실제 길이 vs DataLength 필드)
5. 페이로드 파싱 (상태보고인 경우)

Q: 왜 struct.unpack을 사용하나요?
A: 바이트 배열을 정수로 변환하는 표준 방법입니다.
   '<H'는 Little Endian unsigned short (2 bytes)
   '<I'는 Little Endian unsigned int (4 bytes)

Q: 체크섬 검증을 왜 먼저 하나요?
A: 손상된 패킷을 조기에 걸러내기 위함입니다.
   체크섬이 틀리면 나머지 필드도 신뢰할 수 없습니다.
=============================================================================
"""

import struct
import logging
from typing import Optional, Dict

from .models import ICDHeader, StatusPayload, ParseResult

# 로거 설정
logger = logging.getLogger(__name__)


class ICDParser:
    """
    ICD v1.0 패킷 파서.
    
    VIC↔OCS 통신 패킷을 ICD 규격에 따라 파싱합니다.
    
    특징:
    - 체크섬 검증
    - 상태보고 메시지(0x01) 완전 지원
    - 알 수 없는 메시지 코드도 헤더는 파싱
    
    사용 예시:
        parser = ICDParser()
        result = parser.parse(raw_bytes)
        
        if result.success and result.payload:
            print(f"운용 모드: {result.payload.operation_mode_label}")
            print(f"연결 장치: {result.payload.devices}")
    """
    
    # =========================================================================
    # 클래스 상수
    # - 헤더 크기, 체크섬 크기 등 ICD 규격에서 정의된 값
    # =========================================================================
    HEADER_SIZE = 12          # 헤더 크기 (bytes)
    CHECKSUM_SIZE = 2         # 체크섬 크기 (bytes)
    MIN_PACKET_SIZE = 14      # 최소 패킷 크기 (헤더 + 체크섬)
    
    # 메시지 코드
    MSG_CODE_STATUS_REPORT = 0x01
    
    # =========================================================================
    # 운용 모드 라벨 (bits 7-5)
    # Q: 왜 딕셔너리로 정의하나요?
    # A: 비트 값 → 한글 라벨 매핑을 O(1)로 조회 가능
    #    if-else 체인보다 유지보수가 쉽습니다.
    # =========================================================================
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
    
    # =========================================================================
    # 장치 이름 (bit 0부터 순서대로)
    # ICD 규격: bit 0=VIC, bit 1=RDC, ..., bit 9=TM
    # =========================================================================
    DEVICE_NAMES = [
        "VIC", "RDC", "ADC", "FCAM", "RCAM",
        "ACAM", "SCS", "DIP", "TCC", "TM"
    ]
    
    # =========================================================================
    # 비상정지 원인 이름 (bit 6부터 순서대로)
    # ICD 규격: bits 15-6에 비상정지 원인 플래그
    # =========================================================================
    EMERGENCY_NAMES = [
        "통신 두절",            # bit 6
        "장비고장(주행)",       # bit 7
        "장비고장(동력계)",     # bit 8
        "신호단절(주행)",       # bit 9
        "신호단절(자율)",       # bit 10
        "신호단절(항법)",       # bit 11
        "신호단절(동력계)",     # bit 12
        "신호단절(통신)",       # bit 13
        "수동정지(운용통제장치)", # bit 14
        "수동정지(근거리조종기)", # bit 15
    ]
    
    def __init__(self):
        """
        ICDParser 초기화.
        
        현재는 상태 없는 파서이므로 특별한 초기화 없음.
        향후 통계 추적 등 기능 확장 가능.
        """
        # 파싱 통계 (선택적 기능)
        self._parse_count = 0
        self._success_count = 0
        self._checksum_fail_count = 0
    
    def parse(self, data: bytes) -> ParseResult:
        """
        패킷 파싱 메인 함수.
        
        전체 파싱 플로우를 수행합니다:
        1. 최소 길이 검증
        2. 체크섬 검증
        3. 헤더 파싱
        4. 길이 검증
        5. 페이로드 파싱 (해당되는 경우)
        
        Args:
            data: 원시 패킷 바이트 (UDP 페이로드)
        
        Returns:
            ParseResult 객체 (성공/실패 정보 포함)
        
        Note:
            - 실패해도 예외를 던지지 않고 ParseResult.success=False 반환
            - 부분 성공 가능: 헤더는 파싱됐지만 페이로드 파싱 실패
        """
        self._parse_count += 1
        
        # =====================================================================
        # Step 1: 최소 길이 검증
        # 헤더(12) + 체크섬(2) = 최소 14 bytes 필요
        # =====================================================================
        if len(data) < self.MIN_PACKET_SIZE:
            return ParseResult(
                success=False,
                error=f"Packet too short: {len(data)} < {self.MIN_PACKET_SIZE}",
                raw_size=len(data)
            )
        
        # =====================================================================
        # Step 2: 체크섬 검증
        # 체크섬 = (체크섬 제외 모든 바이트 합) & 0xFFFF
        # =====================================================================
        checksum_ok = self._verify_checksum(data)
        if not checksum_ok:
            self._checksum_fail_count += 1
            # 체크섬 실패해도 헤더 파싱 시도 (디버깅용)
            logger.debug(f"Checksum verification failed for packet of size {len(data)}")
        
        # =====================================================================
        # Step 3: 헤더 파싱
        # =====================================================================
        try:
            header = self._parse_header(data)
        except Exception as e:
            return ParseResult(
                success=False,
                checksum_ok=checksum_ok,
                error=f"Header parsing failed: {str(e)}",
                raw_size=len(data)
            )
        
        # =====================================================================
        # Step 4: 길이 검증
        # 실제 길이 = 헤더(12) + DataLength + 체크섬(2)
        # =====================================================================
        expected_length = self.HEADER_SIZE + header.data_length + self.CHECKSUM_SIZE
        if len(data) != expected_length:
            # 길이 불일치는 경고만 (파싱은 계속)
            logger.warning(
                f"Length mismatch: actual={len(data)}, expected={expected_length}"
            )
        
        # =====================================================================
        # Step 5: 페이로드 파싱 (상태보고 메시지인 경우)
        # =====================================================================
        payload = None
        if header.msg_code == self.MSG_CODE_STATUS_REPORT:
            # 페이로드 시작: 헤더 이후
            payload_data = data[self.HEADER_SIZE:-self.CHECKSUM_SIZE]
            try:
                payload = self._parse_status_payload(payload_data)
            except Exception as e:
                logger.warning(f"Payload parsing failed: {e}")
                # 페이로드 파싱 실패해도 헤더는 유효
        
        # =====================================================================
        # 성공 결과 반환
        # =====================================================================
        self._success_count += 1
        return ParseResult(
            success=True,
            header=header,
            payload=payload,
            checksum_ok=checksum_ok,
            raw_size=len(data)
        )
    
    def _verify_checksum(self, data: bytes) -> bool:
        """
        체크섬 검증.
        
        ICD 규격: 체크섬 = (체크섬 필드 제외 모든 바이트 합) & 0xFFFF
        
        Args:
            data: 전체 패킷 (체크섬 포함)
        
        Returns:
            True if checksum matches
        
        계산 방법:
        1. 패킷에서 마지막 2바이트(체크섬)를 제외한 모든 바이트 합산
        2. 결과를 16비트로 마스킹 (& 0xFFFF)
        3. 패킷의 체크섬 필드와 비교
        """
        if len(data) < self.CHECKSUM_SIZE:
            return False
        
        # 체크섬 제외한 데이터
        data_without_checksum = data[:-self.CHECKSUM_SIZE]
        
        # 수신된 체크섬 추출 (Little Endian 2 bytes)
        # struct.unpack('<H', ...): Little Endian unsigned short
        received_checksum = struct.unpack('<H', data[-self.CHECKSUM_SIZE:])[0]
        
        # 체크섬 계산
        # sum(): 모든 바이트의 정수 값 합산
        # & 0xFFFF: 16비트로 마스킹 (overflow 처리)
        calculated_checksum = sum(data_without_checksum) & 0xFFFF
        
        return calculated_checksum == received_checksum
    
    def _parse_header(self, data: bytes) -> ICDHeader:
        """
        헤더 파싱 (12 bytes).
        
        Args:
            data: 패킷 데이터 (최소 12 bytes)
        
        Returns:
            ICDHeader 객체
        
        바이트 레이아웃:
        - [0:4]: TimeStamp (Little Endian uint32)
        - [3]: Sequence (TimeStamp의 마지막 바이트)
        - [4]: Source ID
        - [5]: Dest ID
        - [6]: MSG Code
        - [7]: ACK Flag
        - [8:10]: Reserved (Little Endian uint16)
        - [10:12]: DataLength (Little Endian uint16)
        """
        # =====================================================================
        # struct.unpack 사용법:
        # '<I': Little Endian unsigned int (4 bytes)
        # '<H': Little Endian unsigned short (2 bytes)
        # [0]: unpack 결과가 튜플이므로 첫 번째 요소 추출
        # =====================================================================
        
        # TimeStamp (4 bytes)
        timestamp = struct.unpack('<I', data[0:4])[0]
        
        # Sequence: timestamp의 마지막 바이트 (8비트, 0-255 롤오버)
        # Q: 왜 data[3]인가요?
        # A: Little Endian이므로 마지막 바이트가 최상위 바이트
        #    실제로는 timestamp의 LSB 부분을 시퀀스로 사용
        sequence = data[3]
        
        # MSG ID (4 bytes를 개별 바이트로 추출)
        source_id = data[4]
        dest_id = data[5]
        msg_code = data[6]
        ack_flag = data[7]
        
        # Reserved (2 bytes)
        reserved = struct.unpack('<H', data[8:10])[0]
        
        # DataLength (2 bytes)
        data_length = struct.unpack('<H', data[10:12])[0]
        
        return ICDHeader(
            timestamp=timestamp,
            sequence=sequence,
            source_id=source_id,
            dest_id=dest_id,
            msg_code=msg_code,
            ack_flag=ack_flag,
            reserved=reserved,
            data_length=data_length
        )
    
    def _parse_status_payload(self, payload: bytes) -> StatusPayload:
        """
        상태보고 메시지 페이로드 파싱.
        
        MSG Code = 0x01인 패킷의 데이터 영역을 파싱합니다.
        
        Args:
            payload: 페이로드 데이터 (최소 5 bytes)
        
        Returns:
            StatusPayload 객체
        
        페이로드 레이아웃:
        - [0:2]: 장치 연결 상태 (Little Endian uint16)
        - [2]: VIC 운용 상태 (1 byte)
        - [3:5]: 비상정지 원인 (Little Endian uint16)
        """
        # =====================================================================
        # 장치 연결 상태 파싱 (2 bytes)
        # bit 0=VIC, bit 1=RDC, ..., bit 9=TM
        # =====================================================================
        device_presence = struct.unpack('<H', payload[0:2])[0]
        devices = {}
        for i, name in enumerate(self.DEVICE_NAMES):
            # (1 << i): i번째 비트 마스크 생성
            # & 연산으로 해당 비트가 1인지 확인
            connected = bool(device_presence & (1 << i))
            devices[name] = connected
        
        # =====================================================================
        # VIC 운용 상태 파싱 (1 byte)
        # bits 7-5: 운용 모드
        # bits 3-2: 운용 권한
        # bits 1-0: 주행 상태
        # =====================================================================
        vic_state = payload[2]
        
        # 비트 추출:
        # >> 5: 오른쪽으로 5비트 시프트 (bits 7-5를 bits 2-0으로 이동)
        # & 0x07: 하위 3비트만 추출 (0b111)
        operation_mode = (vic_state >> 5) & 0x07
        
        # >> 2: 오른쪽으로 2비트 시프트 (bits 3-2를 bits 1-0으로 이동)
        # & 0x03: 하위 2비트만 추출 (0b11)
        authority = (vic_state >> 2) & 0x03
        
        # & 0x03: 하위 2비트만 추출 (bits 1-0)
        driving_state = vic_state & 0x03
        
        # 라벨 변환 (딕셔너리 조회)
        operation_mode_label = self.OPERATION_MODE_LABELS.get(
            operation_mode, f"알 수 없음 ({operation_mode})"
        )
        authority_label = self.AUTHORITY_LABELS.get(
            authority, f"알 수 없음 ({authority})"
        )
        driving_state_label = self.DRIVING_STATE_LABELS.get(
            driving_state, f"알 수 없음 ({driving_state})"
        )
        
        # =====================================================================
        # 비상정지 원인 파싱 (2 bytes)
        # bits 15-6에 10개 비상정지 원인 플래그
        # =====================================================================
        emergency_word = struct.unpack('<H', payload[3:5])[0]
        
        # >> 6: bits 15-6을 bits 9-0으로 이동
        # & 0x3FF: 하위 10비트만 추출 (10개 플래그)
        emergency_bits = (emergency_word >> 6) & 0x3FF
        
        emergency_status = {}
        for i, name in enumerate(self.EMERGENCY_NAMES):
            active = bool(emergency_bits & (1 << i))
            emergency_status[name] = active
        
        return StatusPayload(
            device_presence=device_presence,
            devices=devices,
            vic_state_byte=vic_state,
            operation_mode=operation_mode,
            operation_mode_label=operation_mode_label,
            authority=authority,
            authority_label=authority_label,
            driving_state=driving_state,
            driving_state_label=driving_state_label,
            emergency_word=emergency_word,
            emergency_status=emergency_status
        )
    
    # =========================================================================
    # 통계 메서드 (선택적 기능)
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """파싱 통계 반환."""
        return {
            "parse_count": self._parse_count,
            "success_count": self._success_count,
            "checksum_fail_count": self._checksum_fail_count,
            "success_rate": (
                self._success_count / self._parse_count * 100
                if self._parse_count > 0 else 100.0
            ),
        }
    
    def reset_stats(self) -> None:
        """파싱 통계 초기화."""
        self._parse_count = 0
        self._success_count = 0
        self._checksum_fail_count = 0
