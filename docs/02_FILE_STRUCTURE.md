# UGV-MON 파일 구조

> **최종 업데이트**: 2026-02-09 (리팩터링 v3)

## 디렉토리 구조

```
opus1/
├── run.py                    # 통합 진입점 (CLI)
├── requirements.txt          # 의존성 목록
├── pyproject.toml            # 프로젝트 설정
│
├── tests/                    # 단위 테스트 (50개)
├── docs/                     # 문서
│
└── ugv_mon/                  # 메인 Python 패키지
    ├── __init__.py           # ⭐ 패키지 루트 exports
    ├── app.py                # Dash 앱 팩토리
    ├── styles.py             # UI 스타일 상수
    ├── config.py             # ⭐ 앱 설정 (환경변수)
    ├── constants.py          # ⭐ 상수 정의
    ├── models.py             # ⭐ 데이터 모델 (Enum, ICD)
    │
    │  ════════════════════════════════════════════════
    │  Pipeline (캡처 → 파싱 → 저장)
    │  ════════════════════════════════════════════════
    ├── pipeline/             # 데이터 수집 파이프라인
    │   ├── sniffer.py        # PacketSniffer (Scapy)
    │   ├── queue.py          # PacketQueue (thread-safe)
    │   ├── processor.py      # PacketProcessor (파싱 호출)
    │   └── icd_parser.py     # ICDParser (ICD v1.0)
    │
    │  ════════════════════════════════════════════════
    │  Data Storage
    │  ════════════════════════════════════════════════
    ├── store/                # 데이터 저장소
    │   └── packet_store.py   # 통합 저장소 (deque)
    │
    │  ════════════════════════════════════════════════
    │  Service Layer
    │  ════════════════════════════════════════════════
    ├── services/             # 서비스 레이어
    │   ├── capture_service.py    # 캡처 제어 (start/stop)
    │   ├── stats_service.py      # 통계/연결 상태
    │   ├── ml_service.py         # ML 앙상블 탐지
    │   ├── dashboard_builder.py  # Dict(25키) 빌드
    │   └── service_provider.py   # 콜백 호환 브리지
    │
    │  ════════════════════════════════════════════════
    │  ML Analysis
    │  ════════════════════════════════════════════════
    ├── analysis/             # ML 이상 탐지
    │   ├── ml_pipeline.py    # 메인 파이프라인
    │   ├── ml_anomaly_detector.py  # Isolation Forest
    │   ├── rule_detector.py  # 규칙 기반 탐지
    │   └── feature_extractor.py    # 특성 추출
    │
    │  ════════════════════════════════════════════════
    │  UI Layer
    │  ════════════════════════════════════════════════
    ├── ui/                   # UI 모듈
    │   ├── components/       # 재사용 컴포넌트
    │   │   ├── kpi_card.py       # KPI 카드
    │   │   ├── device_grid.py    # 장치 그리드
    │   │   ├── status_chip.py    # 상태 칩
    │   │   └── log_table.py      # AG-Grid 로그
    │   ├── layouts/          # 레이아웃
    │   │   ├── main_layout.py    # 메인 레이아웃
    │   │   ├── header.py         # 헤더 바
    │   │   ├── panels.py         # 11개 패널
    │   │   └── charts.py         # Plotly 차트
    │   └── ml/               # ML 시각화
    │       ├── anomaly_3d.py     # 3D 산점도
    │       ├── anomaly_timeline.py
    │       └── feature_importance.py
    │
    │  ════════════════════════════════════════════════
    │  Callbacks
    │  ════════════════════════════════════════════════
    ├── callbacks/            # Dash 콜백
    │   └── update_callbacks.py  # 폴링 + UI 갱신
    │
    │  ════════════════════════════════════════════════
    │  DEV/MOCK ONLY (배포 시 제외)
    │  ════════════════════════════════════════════════
    └── mock/                 # ⚠️ 개발/테스트용
        ├── mock_data.py      # Mock 데이터 생성기
        └── live_provider.py  # LEGACY (호환용)
```

## 핵심 파일 역할

### 패키지 루트

| 파일           | 역할                        |
| -------------- | --------------------------- |
| `config.py`    | AppConfig (환경변수, 포트)  |
| `constants.py` | ICD 상수, 디바이스 ID 매핑  |
| `models.py`    | Enum, 데이터클래스 (ICD/UI) |

### Pipeline

| 파일                     | 역할                        |
| ------------------------ | --------------------------- |
| `pipeline/sniffer.py`    | Scapy 기반 UDP 캡처         |
| `pipeline/queue.py`      | 스레드 안전 패킷 큐         |
| `pipeline/processor.py`  | 파싱 → 저장 파이프라인      |
| `pipeline/icd_parser.py` | ICD v1.0 헤더/페이로드 파싱 |

### Service Layer

| 파일                            | 역할                              |
| ------------------------------- | --------------------------------- |
| `services/capture_service.py`   | 캡처 시작/중지/방향전환           |
| `services/stats_service.py`     | 통계 카운터/연결 타임아웃         |
| `services/ml_service.py`        | Rule+ML 앙상블 이상 탐지          |
| `services/dashboard_builder.py` | Dict(25키) 빌드 (순수 함수)       |
| `services/service_provider.py`  | 콜백 호환 브리지 (오케스트레이터) |

### DEV/MOCK ONLY

| 파일                    | 용도                            |
| ----------------------- | ------------------------------- |
| `mock/mock_data.py`     | 개발/테스트용 가짜 데이터       |
| `mock/live_provider.py` | LEGACY (ServiceProvider로 대체) |

## 데이터 흐름

```
Network → Sniffer → Queue → Processor → Store
                                          │
    ┌─────────────────────────────────────┘
    ▼
StatsService ← 통계 집계
    │
    ▼
DashboardBuilder → Dict(25키)
    │
    ▼
ServiceProvider → Callbacks → UI
```

## 실행 방법

```bash
# Mock 모드 (개발/테스트)
python3 run.py --mode mock

# Live 모드 (운영) - ServiceProvider 사용
sudo python3 run.py --mode live --interface eno2

# 테스트
python3 -m pytest tests/ -v
```
