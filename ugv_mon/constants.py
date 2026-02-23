"""
UGV-MON 상수 정의.

프로젝트 전반에서 사용되는 상수를 중앙 집중화합니다.
"""


# =============================================================================
# 장치(Device) 관련 상수
# =============================================================================

DEVICE_IDS: list[str] = ["vic", "rdc", "adc", "fcam", "rcam", "acam", "scs", "dip", "tcc", "tm"]
DEVICE_NAMES: list[str] = ["VIC", "RDC", "ADC", "FCAM", "RCAM", "ACAM", "SCS", "DIP", "TCC", "TM"]

# =============================================================================
# ICD 파서 관련 상수 (헤더 전용)
# =============================================================================

ICD_HEADER_SIZE: int = 12            # 헤더 크기 (bytes)
ICD_CHECKSUM_SIZE: int = 2           # 체크섬 크기 (bytes)
ICD_MIN_PACKET_SIZE: int = ICD_HEADER_SIZE + ICD_CHECKSUM_SIZE

# =============================================================================
# Mock 데이터 상수
# =============================================================================

DEFAULT_INITIAL_SEQUENCE: int = 1000  # Mock 데이터 시작 시퀀스 번호

# =============================================================================
# PacketStore 관련 상수
# =============================================================================

STREAM_RESTART_GAP_MS: int = 3000           # 3초 이상 갭 → 스트림 재시작
JITTER_OUTLIER_THRESHOLD_MS: int = 200      # 200ms 이상 지터 → 이상치
JITTER_NOISE_THRESHOLD_MS: int = 5          # 5ms 이하 변동만 지터로 인정
MAX_CONNECTION_HISTORY: int = 100           # 연결 이력 최대 보관 수
MAX_MODE_TRANSITIONS: int = 50             # 모드 전이 최대 보관 수

# =============================================================================
# ML Service 관련 상수
# =============================================================================

ML_MIN_TRAINING_SAMPLES: int = 120          # 학습에 필요한 최소 샘플 수 (1초 윈도우 기준, ~2분)
ML_MAX_CHART_RECORDS: int = 200             # 3D 차트용 최대 레코드 수
ML_MAX_SCORE_HISTORY: int = 120             # 타임라인용 최대 히스토리 수
ML_DISPLAY_RECORDS: int = 100               # 결과에 포함할 최근 레코드 수
ML_DISPLAY_SCORES: int = 60                 # 결과에 포함할 최근 점수 수
ML_DEFAULT_THRESHOLD: float = -0.3          # 기본 이상 탐지 임계값
ML_RULE_ONLY_CONFIDENCE: float = 0.5        # Rule만 있을 때 기본 신뢰도
ML_FALLBACK_ANOMALY_SCORE: float = -0.5     # ML 없이 이상일 때 대체 점수
ML_RULE_VIOLATED_Z_SCORE: float = 2.5       # Rule 위반 시 기본 Z-score

# =============================================================================
# ML Pipeline / Detector 관련 상수
# =============================================================================

ML_CONTAMINATION: float = 0.10              # 예상 이상치 비율
ML_CACHE_DURATION_SEC: float = 1.0          # 예측 결과 캐시 시간 (초)
ML_N_ESTIMATORS: int = 100                  # Isolation Forest 트리 수
ML_RANDOM_STATE: int = 42                   # 재현성을 위한 랜덤 시드
ML_Z_SCORE_THRESHOLD: float = 2.0           # Z-score 이상 판정 기준
ML_TOP_CONTRIBUTING_FEATURES: int = 3       # 상위 기여 특성 수

# =============================================================================
# Feature Extractor 관련 상수
# =============================================================================

FEATURE_VOLATILITY_MIN_THRESHOLD: float = 0.1   # 변동성 계산 최소 임계값
FEATURE_JITTER_SCALING: float = 0.5              # 지터 점수 스케일링 계수
FEATURE_PPS_SCALING: float = 10.0                # PPS 점수 스케일링 계수
FEATURE_LOSS_SCALING: float = 10.0               # 손실률 점수 스케일링 계수
FEATURE_WEIGHT_JITTER: float = 0.4               # 품질 점수 지터 가중치
FEATURE_WEIGHT_PPS: float = 0.4                  # 품질 점수 PPS 가중치
FEATURE_WEIGHT_LOSS: float = 0.2                 # 품질 점수 손실률 가중치

# =============================================================================
# Service Provider 관련 상수
# =============================================================================

PACKET_QUEUE_MAX_SIZE: int = 1000           # 패킷 큐 최대 크기
PACKET_STORE_WINDOW_SEC: int = 3600         # 패킷 저장소 윈도우 (초)

# =============================================================================
# Mock 데이터 관련 상수 (추가)
# =============================================================================

MOCK_ANOMALY_TOGGLE_PROBABILITY: float = 0.05   # 이상 상태 전환 확률
MOCK_ANOMALY_BASE_PROBABILITY: float = 0.1      # 이상 발생 기본 확률
