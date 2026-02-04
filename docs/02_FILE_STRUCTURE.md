# UGV-MON 파일 구조

> **최종 업데이트**: 2026-02-04

## 디렉토리 구조

```
opus1/
├── run.py                 # 통합 진입점 (CLI: --mode, --interface, --port)
├── requirements.txt       # 의존성 목록
├── test_capture_packets.py  # 통합 테스트
│
├── tests/                 # 단위 테스트 (33개)
│   ├── __init__.py
│   ├── test_icd_parser.py
│   └── test_stats_calculator.py
│
├── docs/                  # 문서 (7개)
│   ├── 00_PROJECT_OVERVIEW.md   # 프로젝트 개요
│   ├── 01_ARCHITECTURE.md       # 아키텍처 설명
│   ├── 02_FILE_STRUCTURE.md     # 파일 구조 (이 문서)
│   ├── 03_ICD_SPECIFICATION.md  # ICD 명세
│   ├── 05_KPI_DATA_ANALYSIS.md  # KPI 상세 설명
│   ├── 07_VISUALIZATION_IDEAS.md # 데이터 분석 아이디어
│   └── 09_MIDTERM_FEEDBACK.md   # 중간발표 피드백
│
├── logs/                  # 로그 폴더
│   └── alerts.log         # 알림 로그 (자동 생성)
│
└── ugv_mon/               # 메인 Python 패키지 (34개 파일)
    ├── app.py             # Dash 앱 팩토리
    ├── config.py          # 설정 관리
    ├── constants.py       # 상수 정의 (장치 목록, ICD 크기 등)
    ├── styles.py          # UI 스타일 상수 (색상, 폰트)
    │
    ├── capture/           # 패킷 캡처 모듈
    │   ├── sniffer.py     # PacketSniffer 클래스
    │   ├── queue.py       # 스레드 안전 PacketQueue
    │   └── stats.py       # CaptureStats 클래스
    │
    ├── parser/            # ICD 파싱 모듈
    │   ├── icd_parser.py  # ICDParser 클래스
    │   └── models.py      # ICDHeader, StatusPayload, ParseResult
    │
    ├── analysis/          # 통계 분석 모듈
    │   ├── stats_calculator.py  # 지터, PPS, 가용성 계산 (window=300초)
    │   └── anomaly_detector.py  # 이상 탐지
    │
    ├── data/              # 데이터 모델 및 제공자
    │   ├── models.py      # 타입 정의 (Enum, dataclass)
    │   ├── mock_data.py   # MockDataGenerator
    │   └── live_provider.py  # LiveDataProvider
    │
    ├── components/        # UI 컴포넌트
    │   ├── status_chip.py # 상태 칩
    │   ├── kpi_card.py    # KPI 카드
    │   ├── device_grid.py # 장치 연결 그리드
    │   ├── log_table.py   # 로그 테이블 (필터링 기능 포함)
    │   └── alerts.py      # 알림 매니저 (토스트)
    │
    ├── layouts/           # 레이아웃
    │   ├── main_layout.py # 전체 레이아웃
    │   ├── header.py      # 헤더 바 (인터페이스 동적 선택)
    │   ├── panels.py      # 상태 패널들
    │   └── charts.py      # 차트
    │
    ├── callbacks/         # Dash 콜백
    │   └── update_callbacks.py  # 폴링 및 UI 업데이트
    │
    └── utils/             # 유틸리티
        └── alert_logger.py  # 알림 로그 기록
```

## 핵심 파일 역할

| 파일 | 역할 |
|------|------|
| `run.py` | 통합 진입점 (CLI: `--mode`, `--interface`, `--port`) |
| `config.py` | 모든 설정 중앙 관리 |
| `constants.py` | 상수 정의 (장치 목록, ICD 크기 등) |
| `styles.py` | UI 스타일 상수 (색상, 폰트) |
| `capture/sniffer.py` | Scapy 패킷 캡처 (BPF 필터링) |
| `parser/icd_parser.py` | ICD v1.0 바이너리 파싱 |
| `analysis/stats_calculator.py` | 지터, PPS, 가용성 계산 (5분 윈도우) |
| `data/live_provider.py` | 캡처+파싱 통합, UI 데이터 제공 |
| `callbacks/update_callbacks.py` | 2초 폴링 및 UI 갱신 |
| `components/alerts.py` | 알림 조건 체크, 토스트 생성 |
| `utils/alert_logger.py` | 알림 로그 파일 기록 |

## 실행 방법

```bash
# Mock 모드 (기본)
python3 run.py
python3 run.py --mode mock

# Live 모드
sudo python3 run.py --mode live --interface lo
sudo python3 run.py --mode live --interface eno2

# 도움말
python3 run.py --help
```

## 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `UGV_MON_USE_LIVE` | `true`면 Live 모드 | Mock 모드 |
| `UGV_MON_INTERFACE` | 캡처 인터페이스 | `lo` |
| `UGV_MON_PORT` | 서버 포트 | `8050` |
| `UGV_MON_DEBUG` | 디버그 모드 | `false` |
| `UGV_MON_POLL_INTERVAL` | 폴링 간격 (ms) | `2000` |
