# UGV-MON 파일 구조

> **최종 업데이트**: 2026-02-06

## 디렉토리 구조

```
opus1/
├── run.py                    # 통합 진입점 (CLI: --mode, --interface, --port)
├── requirements.txt          # 의존성 목록
├── test_capture_packets.py   # 캡처 + PacketStore 통합 테스트
│
├── tests/                    # 단위 테스트
│   ├── __init__.py
│   └── test_icd_parser.py
│
├── scripts/                  # 유틸리티 스크립트
│   └── test_payload_parsing.py
│
├── docs/                     # 문서
│   ├── 00_PROJECT_OVERVIEW.md
│   ├── 01_ARCHITECTURE.md
│   ├── 02_FILE_STRUCTURE.md      # (이 문서)
│   ├── 03_ICD_SPECIFICATION.md
│   ├── 05_KPI_DATA_ANALYSIS.md
│   ├── 11_FINAL_PRESENTATION.md
│   ├── 12_DATA_FLOW_GUIDE.md
│   └── 13_ADVANCED_ANALYSIS_PLAN.md
│
└── ugv_mon/                  # 메인 Python 패키지
    ├── __init__.py
    ├── app.py                # Dash 앱 팩토리
    ├── styles.py             # UI 스타일 상수 (COLORS, CHART_COLORS 등)
    │
    ├── core/                 # 핵심 모듈 (설정, 상수, 모델)
    │   ├── __init__.py       # models + config + constants 통합 export
    │   ├── models.py         # Enum, ICD 모델, UI 모델 통합
    │   ├── config.py         # AppConfig (환경변수 기반 설정)
    │   └── constants.py      # DEVICE_IDS, DEVICE_NAMES, 프로토콜 상수
    │
    ├── capture/              # 패킷 캡처 모듈
    │   ├── __init__.py
    │   ├── sniffer.py              # PacketSniffer (Scapy BPF 필터)
    │   ├── queue.py                # PacketQueue (thread-safe deque)
    │   ├── stats.py                # CaptureStats (캡처 레벨 카운터)
    │   └── packet_processor.py     # PacketProcessor (queue->parser->store)
    │
    ├── parser/               # ICD 파싱 모듈
    │   ├── __init__.py
    │   └── icd_parser.py           # ICDParser (비트마스킹, 체크섬)
    │
    ├── data/                 # 데이터 저장 및 제공
    │   ├── __init__.py
    │   ├── packet_store.py         # PacketStore (단일 deque, 통계, 이력)
    │   ├── types.py                # DashboardData TypedDict (25키)
    │   ├── live_provider.py        # LiveDataProvider (캡처 제어 + Dict 빌드)
    │   └── mock_data.py            # MockDataGenerator (테스트용)
    │
    ├── components/           # UI 컴포넌트
    │   ├── __init__.py
    │   ├── status_chip.py          # 상태 칩 (연결, 방향)
    │   ├── kpi_card.py             # KPI 카드 (7개)
    │   ├── device_grid.py          # 장치 그리드 (5x2)
    │   └── log_table.py            # AG-Grid 로그 테이블
    │
    ├── layouts/              # 레이아웃
    │   ├── __init__.py
    │   ├── main_layout.py          # 메인 레이아웃 (MantineProvider)
    │   ├── header.py               # 헤더 바 (연결 토글, 방향 전환)
    │   ├── panels.py               # 전체 대시보드 패널 (단일 파일)
    │   └── charts.py               # Plotly 차트 (PPS+지터, 가용성)
    │
    └── callbacks/            # Dash 콜백
        ├── __init__.py
        └── update_callbacks.py     # 폴링 + UI 갱신 + 제어 콜백
```

## 핵심 파일 역할

| 파일 | 역할 |
|------|------|
| `run.py` | 통합 진입점 (CLI: `--mode`, `--interface`, `--port`) |
| `core/models.py` | 전체 데이터 모델 통합 (Enum, ICD, UI, 매핑 테이블) |
| `core/config.py` | 환경변수 기반 설정 관리 |
| `capture/packet_processor.py` | 패킷 처리 파이프라인 (queue->parser->store, 이력 기록) |
| `data/packet_store.py` | 통합 저장소 (deque 1개로 모든 통계/이력/차트 관리) |
| `data/types.py` | DashboardData TypedDict (25개 키 타입 정의) |
| `data/live_provider.py` | 캡처 제어 + DashboardData Dict(25키) 빌드 |
| `layouts/panels.py` | 10개 대시보드 패널 (운용, 비상, 장치, 차트, 이력 등) |
| `callbacks/update_callbacks.py` | 2초 폴링, UI 갱신, 연결/방향 제어 콜백 |

## 데이터 흐름 (파일 순서)

```
1. sniffer.py           ->  UDP 캡처 -> Tuple[datetime, bytes]
2. queue.py             ->  deque 저장
3. packet_processor.py  ->  언패킹 + 파싱 + store.add() + 이력 기록
4. packet_store.py      ->  통합 저장 (deque[PacketRecord])
5. live_provider.py     ->  _build_dashboard_data() -> Dict(25키)
6. update_callbacks.py  ->  UI 컴포넌트 변환 (15개 Output)
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
