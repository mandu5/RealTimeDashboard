# UGV-MON 파일 구조

> **최종 업데이트**: 2026-02-04

## 디렉토리 구조

```
ugv_mon/
├── run.py                 # 통합 진입점 (CLI: --mode, --interface, --port)
├── requirements.txt       # 의존성 목록
├── test_capture_packets.py  # 통합 테스트
│
├── tests/                 # 단위 테스트 (33개)
│   ├── __init__.py
│   ├── test_icd_parser.py
│   └── test_stats_calculator.py
│
├── docs/                  # 문서
│   ├── 00_PROJECT_OVERVIEW.md
│   ├── 01_ARCHITECTURE.md
│   ├── 02_FILE_STRUCTURE.md     # (이 문서)
│   ├── 03_ICD_SPECIFICATION.md
│   ├── 05_KPI_DATA_ANALYSIS.md
│   ├── 12_DATA_FLOW_GUIDE.md
│   ├── 13_ADVANCED_ANALYSIS_PLAN.md
│   └── 14_DATA_FLOW_SIMPLE.md   # 간단한 데이터 흐름
│
└── ugv_mon/               # 메인 Python 패키지
    ├── app.py             # Dash 앱 팩토리
    ├── config.py          # 설정 관리
    ├── constants.py       # 상수 정의
    ├── styles.py          # UI 스타일 상수
    │
    ├── capture/           # 패킷 캡처 모듈
    │   ├── sniffer.py           # PacketSniffer (Scapy)
    │   ├── queue.py             # PacketQueue (thread-safe)
    │   ├── stats.py             # CaptureStats (캡처 카운터)
    │   └── packet_processor.py  # PacketProcessor (NEW) ★
    │
    ├── parser/            # ICD 파싱 모듈
    │   ├── icd_parser.py        # ICDParser
    │   └── models.py            # ICDHeader, OperationalPayload
    │
    ├── analysis/          # 통계 분석 모듈
    │   ├── stats_calculator.py  # StatsCalculator (하위호환)
    │   └── anomaly_detector.py  # 이상 탐지
    │
    ├── data/              # 데이터 모델 및 제공자
    │   ├── packet_store.py      # PacketStore (NEW) ★ 통합 저장소
    │   ├── types.py             # TypedDict 정의 (NEW) ★
    │   ├── live_provider.py     # LiveDataProvider
    │   ├── mock_data.py         # MockDataGenerator
    │   └── models.py            # 타입 정의
    │
    ├── components/        # UI 컴포넌트
    │   ├── status_chip.py
    │   ├── kpi_card.py
    │   ├── device_grid.py
    │   └── log_table.py
    │
    ├── layouts/           # 레이아웃
    │   ├── main_layout.py
    │   ├── header.py
    │   ├── panels/
    │   └── charts.py
    │
    ├── callbacks/         # Dash 콜백
    │   └── update_callbacks.py
    │
    └── core/              # 공통 모듈
        ├── __init__.py
        └── models.py
```

## 핵심 파일 역할

### 새로 추가된 파일 (2026-02-04) ★

| 파일 | 역할 |
|------|------|
| `capture/packet_processor.py` | 패킷 처리 파이프라인 (언패킹, 파싱, 저장) |
| `data/packet_store.py` | 통합 저장소 (deque 1개로 모든 데이터 관리) |
| `data/types.py` | TypedDict 정의 (DashboardData 25개 키) |

### 기존 파일

| 파일 | 역할 |
|------|------|
| `run.py` | 통합 진입점 (CLI: `--mode`, `--interface`, `--port`) |
| `config.py` | 모든 설정 중앙 관리 |
| `capture/sniffer.py` | Scapy 패킷 캡처 (BPF 필터링) |
| `capture/queue.py` | 스레드 안전 패킷 버퍼 |
| `parser/icd_parser.py` | ICD v1.0 바이너리 파싱 |
| `data/live_provider.py` | 캡처 제어 + DashboardData 생성 |
| `callbacks/update_callbacks.py` | 2초 폴링 및 UI 갱신 |

## 데이터 흐름 (파일 순서)

```
1. sniffer.py      →  UDP 캡처 → Tuple[datetime, bytes]
2. queue.py        →  deque 저장
3. packet_processor.py  →  언패킹 + 파싱 + 저장
4. packet_store.py →  통합 저장 (deque[PacketRecord])
5. live_provider.py →  Dict(25키) 생성
6. update_callbacks.py →  UI 컴포넌트 변환
```

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
