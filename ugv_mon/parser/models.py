"""
ICD Parser Data Models.

ICD v1.0 규격에 따른 파싱 결과 데이터 구조를 정의합니다.

=============================================================================
데이터 구조:
1. ICDHeader: 12바이트 헤더 정보
2. StatusPayload: 상태보고 메시지(0x01) 페이로드
3. ParseResult: 파싱 결과 컨테이너

Q: 왜 dataclass를 사용하나요?
A: 1. 타입 안전성: 필드 타입이 명시되어 IDE 자동완성 지원
   2. 불변성 지원: frozen=True로 불변 객체 생성 가능
   3. 자동 메서드: __init__, __repr__, __eq__ 자동 생성
   4. 문서화: 필드 선언 자체가 문서 역할
=============================================================================
"""

from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class ICDHeader:
    """
    ICD v1.0 헤더 정보 (12 bytes).
    
    패킷의 헤더 부분을 파싱한 결과를 담습니다.
    
    Attributes:
        timestamp: 4바이트 타임스탬프 원본 값
        sequence: 시퀀스 번호 (timestamp의 마지막 바이트, 0-255)
        source_id: 송신 장비 ID
        dest_id: 수신 장비 ID
        msg_code: 메시지 코드 (0x01=상태보고)
        ack_flag: ACK 플래그
        reserved: 예약 필드 (2 bytes)
        data_length: 데이터 영역 길이
    
    바이트 위치:
        - [0:4]: timestamp (Little Endian uint32)
        - [3]: sequence (timestamp의 마지막 바이트)
        - [4]: source_id
        - [5]: dest_id
        - [6]: msg_code
        - [7]: ack_flag
        - [8:10]: reserved (Little Endian uint16)
        - [10:12]: data_length (Little Endian uint16)
    """
    timestamp: int      # 전체 타임스탬프 값
    sequence: int       # 시퀀스 번호 (0-255, 롤오버)
    source_id: int      # 송신 장비 ID
    dest_id: int        # 수신 장비 ID
    msg_code: int       # 메시지 코드 (0x01 = 상태보고)
    ack_flag: int       # ACK 플래그
    reserved: int       # 예약 필드
    data_length: int    # 데이터 영역 길이
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환 (UI 표시용)."""
        return {
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "source_id": f"0x{self.source_id:02X}",
            "dest_id": f"0x{self.dest_id:02X}",
            "msg_code": f"0x{self.msg_code:02X}",
            "ack_flag": f"0x{self.ack_flag:02X}",
            "data_length": self.data_length,
        }


@dataclass
class StatusPayload:
    """
    상태보고 메시지 페이로드 (MSG Code = 0x01).
    
    VIC의 현재 상태를 담은 페이로드입니다.
    
    Attributes:
        device_presence: 장치 연결 상태 비트워드
        devices: 개별 장치 연결 상태 딕셔너리
        vic_state_byte: VIC 상태 원본 바이트
        operation_mode: 운용 모드 (bits 7-5)
        authority: 운용 권한 (bits 3-2)
        driving_state: 주행 상태 (bits 1-0)
        emergency_word: 비상정지 원인 비트워드
        emergency_status: 개별 비상정지 원인 딕셔너리
    
    운용 모드 값:
        - 0b000: 준비 (PREP)
        - 0b001: 전환 중 (TRANSITION)
        - 0b010: 무인 주행 (UNMANNED DRIVING)
        - 0b011: 무인 사격 (UNMANNED FIRING)
        - 0b100: 비상 정지 (EMERGENCY STOP)
    
    운용 권한 값:
        - 0b00: 해제됨 (RELEASED)
        - 0b01: OCS 획득 (OCS ACQUIRED)
        - 0b10: 근거리조종기 (NEAR CONTROLLER)
    
    주행 상태 값:
        - 0b01: 원격 (REMOTE)
        - 0b10: 종속주행 (PLATOONING)
        - 0b11: 자율배치 (AUTONOMOUS DISPATCH)
    """
    # 장치 연결 상태
    device_presence: int              # 원본 비트워드
    devices: Dict[str, bool]          # 장치별 연결 상태
    
    # VIC 운용 상태
    vic_state_byte: int               # 원본 바이트
    operation_mode: int               # bits 7-5
    operation_mode_label: str         # 한글 라벨
    authority: int                    # bits 3-2
    authority_label: str              # 한글 라벨
    driving_state: int                # bits 1-0
    driving_state_label: str          # 한글 라벨
    
    # 비상정지 원인
    emergency_word: int               # 원본 비트워드
    emergency_status: Dict[str, bool] # 비상정지 원인별 상태
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환 (UI 표시용)."""
        return {
            "devices": self.devices,
            "operation_mode": self.operation_mode_label,
            "authority": self.authority_label,
            "driving_state": self.driving_state_label,
            "emergency_status": self.emergency_status,
        }


@dataclass
class ParseResult:
    """
    패킷 파싱 결과.
    
    ICDParser.parse()의 반환 타입입니다.
    파싱 성공 여부와 결과 데이터를 담습니다.
    
    Attributes:
        success: 파싱 성공 여부
        header: 파싱된 헤더 (성공 시)
        payload: 파싱된 페이로드 (상태보고인 경우)
        checksum_ok: 체크섬 검증 결과
        error: 오류 메시지 (실패 시)
        raw_size: 원본 패킷 크기
    
    사용 예시:
        result = parser.parse(raw_bytes)
        
        if result.success:
            # 성공: 헤더와 페이로드 사용
            print(result.header.sequence)
        else:
            # 실패: 오류 메시지 확인
            print(result.error)
    """
    success: bool                           # 파싱 성공 여부
    header: Optional[ICDHeader] = None      # 헤더 (성공 시)
    payload: Optional[StatusPayload] = None # 페이로드 (상태보고 시)
    checksum_ok: bool = False               # 체크섬 검증 결과
    error: Optional[str] = None             # 오류 메시지
    raw_size: int = 0                       # 원본 패킷 크기
    
    @property
    def is_status_report(self) -> bool:
        """상태보고 메시지인지 확인."""
        return (
            self.success and 
            self.header is not None and 
            self.header.msg_code == 0x01
        )
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환 (디버깅/로깅용)."""
        result = {
            "success": self.success,
            "checksum_ok": self.checksum_ok,
            "raw_size": self.raw_size,
        }
        if self.header:
            result["header"] = self.header.to_dict()
        if self.payload:
            result["payload"] = self.payload.to_dict()
        if self.error:
            result["error"] = self.error
        return result
