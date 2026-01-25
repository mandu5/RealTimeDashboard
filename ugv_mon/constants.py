"""
UGV-MON 상수 정의.

프로젝트 전반에서 사용되는 상수를 중앙 집중화하여 DRY 원칙을 준수합니다.
"""

from typing import List, Dict

# =============================================================================
# 장치(Device) 관련 상수
# =============================================================================

# 장치 ID (소문자, 내부 식별자)
DEVICE_IDS: List[str] = [
    "vic", "rdc", "adc", "fcam", "rcam", "acam", "scs", "dip", "tcc", "tm"
]

# 장치 이름 (대문자, 표시용)
DEVICE_NAMES: List[str] = [
    "VIC", "RDC", "ADC", "FCAM", "RCAM", "ACAM", "SCS", "DIP", "TCC", "TM"
]

# 장치 ID → 이름 매핑
DEVICE_ID_TO_NAME: Dict[str, str] = dict(zip(DEVICE_IDS, DEVICE_NAMES))

# =============================================================================
# 시퀀스/패킷 관련 상수
# =============================================================================

# 시퀀스 번호 최대값 (8비트, 0-255 순환)
MAX_SEQUENCE: int = 256

# Mock 모드 초기 시퀀스 번호
DEFAULT_INITIAL_SEQUENCE: int = 49195

# 예상 PPS (Packets Per Second)
EXPECTED_PPS: int = 1000

# =============================================================================
# ICD 파서 관련 상수
# =============================================================================

# ICD 헤더 크기 (bytes)
ICD_HEADER_SIZE: int = 12

# 체크섬 크기 (bytes)
ICD_CHECKSUM_SIZE: int = 2

# 최소 패킷 크기 (헤더 + 체크섬)
ICD_MIN_PACKET_SIZE: int = ICD_HEADER_SIZE + ICD_CHECKSUM_SIZE

# 상태보고 메시지 코드
MSG_CODE_STATUS_REPORT: int = 0x01

# =============================================================================
# 운용 모드/상태 라벨
# =============================================================================

OPERATION_MODE_LABELS: Dict[int, str] = {
    0b000: "준비 (PREP)",
    0b001: "전환 중 (TRANSITION)",
    0b010: "무인 주행 (UNMANNED DRIVING)",
    0b011: "무인 사격 (UNMANNED FIRING)",
    0b100: "비상 정지 (EMERGENCY STOP)",
}

AUTHORITY_LABELS: Dict[int, str] = {
    0b00: "해제됨 (RELEASED)",
    0b01: "OCS 획득 (OCS ACQUIRED)",
    0b10: "근거리조종기 (NEAR CONTROLLER)",
}

DRIVING_STATE_LABELS: Dict[int, str] = {
    0b01: "원격 (REMOTE)",
    0b10: "종속주행 (PLATOONING)",
    0b11: "자율배치 (AUTONOMOUS DISPATCH)",
}

# 비상정지 원인 라벨 (bit 6~15 순서)
EMERGENCY_LABELS: List[str] = [
    "통신 두절",
    "장비고장(주행)",
    "장비고장(동력계)",
    "신호단절(주행)",
    "신호단절(자율)",
    "신호단절(항법)",
    "신호단절(동력계)",
    "신호단절(통신)",
    "수동정지(운용통제장치)",
    "수동정지(근거리조종기)",
]
