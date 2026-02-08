"""
UGV-MON 상수 정의.

프로젝트 전반에서 사용되는 상수를 중앙 집중화합니다.
"""


# =============================================================================
# 장치(Device) 관련 상수
# =============================================================================

DEVICE_IDS: list[str] = ["vic", "rdc", "adc", "fcam", "rcam", "acam", "scs", "dip", "tcc", "tm"]
DEVICE_NAMES: list[str] = ["VIC", "RDC", "ADC", "FCAM", "RCAM", "ACAM", "SCS", "DIP", "TCC", "TM"]
DEVICE_ID_TO_NAME: dict[str, str] = dict(zip(DEVICE_IDS, DEVICE_NAMES))

# =============================================================================
# 시퀀스/패킷 관련 상수
# =============================================================================

SEQ_MODULO: int = 16                 # 시퀀스 번호 모듈로 (4비트: 0~15)
DEFAULT_INITIAL_SEQUENCE: int = 49195  # Mock 모드 초기값
EXPECTED_PPS: int = 1000             # 예상 PPS

# =============================================================================
# ICD 파서 관련 상수 (헤더 전용)
# =============================================================================

ICD_HEADER_SIZE: int = 12            # 헤더 크기 (bytes)
ICD_CHECKSUM_SIZE: int = 2           # 체크섬 크기 (bytes)
ICD_MIN_PACKET_SIZE: int = ICD_HEADER_SIZE + ICD_CHECKSUM_SIZE

# =============================================================================
# 페이로드 관련 상수 - ICD 명세 확정 후 활성화 예정
# =============================================================================
# OPERATION_MODE_LABELS, AUTHORITY_LABELS, DRIVING_STATE_LABELS, EMERGENCY_LABELS
# → ICD 명세 확정 시 아래 주석 해제하여 사용

# OPERATION_MODE_LABELS: Dict[int, str] = {
#     0b000: "준비 (PREP)",
#     0b001: "전환 중 (TRANSITION)",
#     0b010: "무인 주행 (UNMANNED DRIVING)",
#     0b011: "무인 사격 (UNMANNED FIRING)",
#     0b100: "비상 정지 (EMERGENCY STOP)",
# }
# AUTHORITY_LABELS: Dict[int, str] = {...}
# DRIVING_STATE_LABELS: Dict[int, str] = {...}
# EMERGENCY_LABELS: List[str] = [...]
