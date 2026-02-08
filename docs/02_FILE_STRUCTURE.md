# UGV-MON 파일 구조

> **최종 업데이트**: 2026-02-08

## 디렉토리 구조

```
opus1/
├── run.py                    # 통합 진입점 (CLI: --mode, --interface, --port)
├── requirements.txt          # 의존성 목록
├── pyproject.toml            # 프로젝트 설정 (pytest, mypy)
├── ruff.toml                 # 린터 설정
│
├── tests/                    # 단위 테스트 (52개)
│   ├── test_icd_parser.py         # ICD 파서 테스트
│   ├── test_packet_store.py       # PacketStore 테스트
│   └── test_ml_anomaly_detector.py  # ML 탐지기 테스트
│
├── scripts/                  # 유틸리티 스크립트
│   └── test_payload_parsing.py
│
├── docs/                     # 문서
│   ├── 00_PROJECT_OVERVIEW.md
│   ├── 01_ARCHITECTURE.md
│   ├── 02_FILE_STRUCTURE.md      # (이 문서)
│   ├── 03_ICD_SPECIFICATION.md
│   ├── 04_KPI_METRICS.md
│   ├── 05_ML_ANOMALY_DETECTION.md
│   ├── 06_DATA_FLOW_GUIDE.md
│   ├── 07_OJT_WEEKLY_LOGS.md
│   └── Final_Project_Report.md
│
└── ugv_mon/                  # 메인 Python 패키지
    ├── app.py                # Dash 앱 팩토리
    ├── styles.py             # UI 스타일 상수 (COLORS 등)
    │
    ├── core/                 # 핵심 모듈
    │   ├── models.py         # 통합 데이터 모델 (Enum, ICD, UI)
    │   ├── config.py         # AppConfig (환경변수 기반)
    │   └── constants.py      # 장치ID, 포트, 프로토콜 상수
    │
    ├── capture/              # 패킷 캡처 모듈
    │   ├── sniffer.py        # PacketSniffer (Scapy BPF 필터)
    │   ├── queue.py          # PacketQueue (thread-safe deque)
    │   ├── stats.py          # CaptureStats (캡처 레벨 카운터)
    │   └── packet_processor.py  # PacketProcessor (queue→parser→store)
    │
    ├── parser/               # ICD 파싱 모듈
    │   └── icd_parser.py     # ICDParser (비트마스킹, 체크섬)
    │
    ├── data/                 # 데이터 저장 및 제공
    │   ├── packet_store.py   # PacketStore (단일 deque, 통계, 이력)
    │   ├── types.py          # DashboardData TypedDict (25키)
    │   ├── live_provider.py  # LiveDataProvider (캡처 제어 + Dict)
    │   └── mock_data.py      # MockDataGenerator (테스트용)
    │
    ├── analysis/             # ML 이상 탐지
    │   ├── ml_pipeline.py          # 메인 파이프라인 (MLPipeline)
    │   ├── ml_anomaly_detector.py  # Isolation Forest 탐지기
    │   ├── rule_detector.py        # 규칙 기반 탐지기
    │   └── feature_extractor.py    # 특성 추출기
    │
    ├── components/           # UI 컴포넌트
    │   ├── kpi_card.py       # KPI 카드 (8개)
    │   ├── device_grid.py    # 장치 그리드 (5x2)
    │   ├── status_chip.py    # 상태 칩 (연결, 방향)
    │   └── log_table.py      # AG-Grid 로그 테이블
    │
    ├── layouts/              # 레이아웃
    │   ├── main_layout.py    # 메인 레이아웃 (MantineProvider)
    │   ├── header.py         # 헤더 바 (연결 토글)
    │   ├── panels.py         # 전체 대시보드 패널 (12개)
    │   ├── charts.py         # Plotly 차트 (PPS+지터, 가용성)
    │   └── ml_charts/        # ML 시각화 차트
    │       ├── anomaly_3d.py       # 3D 산점도 (PCA)
    │       ├── anomaly_timeline.py # 이상 타임라인
    │       ├── confidence_gauge.py # 신뢰도 게이지
    │       └── feature_importance.py # 기여 특성 차트
    │
    └── callbacks/            # Dash 콜백
        └── update_callbacks.py  # 폴링 + UI 갱신 + ML 콜백
```

## 핵심 파일 역할

| 파일                            | 역할                                                         |
| ------------------------------- | ------------------------------------------------------------ |
| `run.py`                        | 통합 진입점 (CLI: `--mode`, `--interface`, `--port`)         |
| `core/models.py`                | 전체 데이터 모델 통합 (Enum, ICD, UI, 매핑)                  |
| `core/config.py`                | 환경변수 기반 설정 관리                                      |
| `capture/packet_processor.py`   | 패킷 처리 파이프라인 (queue→parser→store)                    |
| `data/packet_store.py`          | **통합 저장소** (deque 1개로 모든 통계/이력/차트)            |
| `data/types.py`                 | DashboardData TypedDict (25개 키 타입 정의)                  |
| `data/live_provider.py`         | **Facade + Orchestrator**: 캡처 제어 + 상태 관리 + Dict 빌드 |
| `analysis/ml_pipeline.py`       | ML 이상 탐지 파이프라인                                      |
| `layouts/panels.py`             | 12개 대시보드 패널                                           |
| `callbacks/update_callbacks.py` | 2초 폴링, UI 갱신, ML 콜백                                   |

## 데이터 흐름

```
1. sniffer.py           →  UDP 캡처 → (datetime, bytes)
2. queue.py             →  deque 저장
3. packet_processor.py  →  언패킹 + 파싱 + store.add() + 이력 기록
4. packet_store.py      →  통합 저장 (deque[PacketRecord])
5. live_provider.py     →  _build_dashboard_data() → Dict(25키)
6. update_callbacks.py  →  UI 컴포넌트 변환 (15개 Output)
```

## 실행 방법

```bash
# Mock 모드 (기본)
python3 run.py
python3 run.py --mode mock

# Live 모드
sudo python3 run.py --mode live --interface lo
sudo python3 run.py --mode live --interface eno2

# 테스트
python3 -m pytest tests/ -v

# 도움말
python3 run.py --help
```
