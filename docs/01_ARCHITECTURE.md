# UGV-MON 아키텍처

> **최종 업데이트**: 2026-02-08

## 시스템 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                          UGV-MON                                 │
├─────────────────────────────────────────────────────────────────┤
│   [Capture Layer]                                                │
│   └── PacketSniffer (Scapy) → PacketQueue → PacketProcessor      │
├─────────────────────────────────────────────────────────────────┤
│   [Data Layer]                                                   │
│   └── PacketStore (deque) → LiveDataProvider (Dict 25키)         │
├─────────────────────────────────────────────────────────────────┤
│   [Analysis Layer]                                               │
│   └── MLPipeline (Isolation Forest) + RuleDetector (앙상블)      │
├─────────────────────────────────────────────────────────────────┤
│   [Presentation Layer]                                            │
│   └── Dash App → Callbacks → UI Components (12개 패널)           │
└─────────────────────────────────────────────────────────────────┘
```

## 데이터 흐름

```
Network → Sniffer → Queue → Processor → Store → Provider → Callbacks → UI
  (UDP)   (bytes)  (deque)  (파싱)     (deque)  (Dict)    (15 Output)
```

### 상세 흐름

1. **sniffer.py**: UDP 패킷 캡처 → `(datetime, bytes)` 튜플
2. **queue.py**: 스레드 안전 큐에 저장
3. **packet_processor.py**: 파싱 + `PacketStore.add()` + 이력 기록
4. **packet_store.py**: `deque[PacketRecord]` 단일 저장
5. **live_provider.py**: `_build_dashboard_data()` → Dict(25키)
6. **update_callbacks.py**: UI 컴포넌트 변환 (15개 Output)

## 책임 분리

| 컴포넌트             | 역할                                                       |
| -------------------- | ---------------------------------------------------------- |
| **PacketProcessor**  | queue → 파싱 → store 저장 (파싱은 여기서만)                |
| **PacketStore**      | 단일 deque 저장 + 통계/이력 제공                           |
| **LiveDataProvider** | **Facade + Orchestrator**: 캡처 제어, 상태 관리, Dict 빌드 |

### LiveDataProvider 역할 상세

1. **캡처 컴포넌트 초기화**: sniffer, queue, parser, store, processor 생성
2. **캡처 제어**: start/stop/toggle_direction
3. **상태 관리**: 연결 상태, 자체 카운터 (total_packets, parse_success)
4. **가용성 세그먼트**: 회사 방식 uptime 구간 기록
5. **ML 파이프라인**: 초기화 및 조율
6. **Dict(25키) 빌드**: Store + 자체 상태 조합

## 모듈 구조

```
ugv_mon/
├── core/                 # 핵심 모듈
│   ├── models.py         # 통합 데이터 모델 (Enum, ICD, UI)
│   ├── config.py         # 앱 설정 (환경변수 기반)
│   └── constants.py      # 상수 정의 (장치ID, 포트)
│
├── capture/              # 패킷 캡처
│   ├── sniffer.py        # Scapy 스니퍼 (BPF 필터)
│   ├── queue.py          # 스레드 안전 큐
│   ├── stats.py          # 캡처 카운터
│   └── packet_processor.py  # 처리 파이프라인
│
├── parser/               # ICD 파싱
│   └── icd_parser.py     # 메인 파서 (비트마스킹, 체크섬)
│
├── data/                 # 데이터 저장 및 제공
│   ├── packet_store.py   # 통합 저장소 (단일 deque)
│   ├── types.py          # DashboardData TypedDict (25키)
│   ├── live_provider.py  # 캡처 제어 + Dict 빌드
│   └── mock_data.py      # 테스트 데이터 생성기
│
├── analysis/             # ML 이상 탐지
│   ├── ml_pipeline.py    # 메인 파이프라인
│   ├── ml_anomaly_detector.py  # Isolation Forest
│   ├── rule_detector.py  # 규칙 기반 탐지
│   └── feature_extractor.py  # 특성 추출
│
├── components/           # UI 컴포넌트
│   ├── kpi_card.py       # KPI 카드 (8개)
│   ├── device_grid.py    # 장치 그리드 (5x2)
│   ├── status_chip.py    # 상태 칩
│   └── log_table.py      # AG-Grid 로그
│
├── layouts/              # 레이아웃
│   ├── main_layout.py    # 메인 레이아웃
│   ├── header.py         # 헤더 바
│   ├── panels.py         # 전체 패널 (단일 파일)
│   ├── charts.py         # Plotly 차트
│   └── ml_charts/        # ML 시각화
│       ├── anomaly_3d.py       # 3D 산점도
│       ├── anomaly_timeline.py # 타임라인
│       ├── confidence_gauge.py # 신뢰도 게이지
│       └── feature_importance.py # 기여 특성
│
└── callbacks/            # Dash 콜백
    └── update_callbacks.py  # 폴링 + UI 갱신
```

## PacketStore 설계

모든 통계/UI 데이터를 단일 deque에서 제공:

```python
PacketStore (deque[PacketRecord])
├── get_stats_dict()         → KPI 통계
├── get_jitter_p95()         → 지터 백분위
├── get_pps()                → 초당 패킷 수
├── get_packet_loss()        → 패킷 손실
├── get_availability()       → 가용성 (5분/1시간)
├── get_logs()               → 로그 UI
├── get_chart_data()         → 차트 UI
├── get_stats_by_code()      → msg_code별 통계
├── get_connection_history() → 연결 이력
├── get_mode_transitions()   → 모드 전이 이력
└── get_emergency_counts()   → 비상정지 통계
```

## 폴링 사이클 (2초)

```
dcc.Interval (2초)
     │
     ▼
update_dashboard_data()
     │
     ├── processor.process_pending()  → 패킷 처리
     │        │
     │        └── store.add()         → 저장
     │
     └── provider._build_dashboard_data()  → Dict(25키)
            │
            ├── _build_connection_info()    (5키)
            ├── _build_kpi_metrics()        (8키)
            ├── _build_operational_info()   (4키)
            └── _build_ui_display_data()    (8키)
                   │
                   ▼
            dashboard-data Store 갱신
                   │
                   ▼
            UI 컴포넌트 갱신 (15개 Output)
```

## 설계 결정

| 결정      | 선택              | 이유                     |
| --------- | ----------------- | ------------------------ |
| 갱신 방식 | Polling (2초)     | 단순성, 안정성           |
| 저장소    | 단일 deque        | 중복 제거, 유지보수 용이 |
| ML 모델   | Isolation Forest  | 비지도 학습, 실시간 적용 |
| Mock/Live | 다형성 인터페이스 | 동일 UI로 테스트/운용    |
