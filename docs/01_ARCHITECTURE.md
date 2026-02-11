# UGV-MON 아키텍처

> **최종 업데이트**: 2026-02-08 (리팩터링 v2)

## 시스템 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                          UGV-MON                                 │
├─────────────────────────────────────────────────────────────────┤
│   [Pipeline Layer]                                               │
│   └── PacketSniffer → PacketQueue → PacketProcessor              │
├─────────────────────────────────────────────────────────────────┤
│   [Service Layer]                                                │
│   ├── CaptureService    (캡처 제어)                              │
│   ├── StatsService      (통계 관리)                              │
│   ├── MLService         (이상 탐지)                              │
│   └── DashboardBuilder  (Dict 빌드)                              │
├─────────────────────────────────────────────────────────────────┤
│   [Store Layer]                                                  │
│   └── PacketStore (deque) ← 통합 저장소                          │
├─────────────────────────────────────────────────────────────────┤
│   [UI Layer]                                                     │
│   └── Dash App → Callbacks → UI (11개 패널)                      │
└─────────────────────────────────────────────────────────────────┘
```

## 데이터 흐름 (단방향)

```
Network → Sniffer → Queue → Processor → Store
                                          │
               ┌──────────────────────────┘
               ▼
         StatsService (통계 집계)
               │
               ▼
         DashboardBuilder (Dict 25키)
               │
               ▼
         ServiceProvider (조율)
               │
               ▼
         Callbacks → UI
```

### 폴링 사이클 (2초)

```
dcc.Interval (2초)
     │
     ▼
1. processor.process_pending()  → Store 저장
     │
2. stats.update(result)         → 통계 집계
     │
3. ml.predict(store)            → 이상 탐지
     │
4. builder.build(...)           → Dict(25키)
     │
     ▼
dashboard-data Store → UI 갱신
```

## 책임 분리 (Service Layer)

| 컴포넌트             | 책임                        | 파일                            |
| -------------------- | --------------------------- | ------------------------------- |
| **CaptureService**   | 캡처 시작/중지/방향전환     | `services/capture_service.py`   |
| **StatsService**     | 통계 카운터/연결 타임아웃   | `services/stats_service.py`     |
| **MLService**        | Rule+ML 앙상블 탐지         | `services/ml_service.py`        |
| **DashboardBuilder** | Dict(25키) 빌드 (순수 함수) | `services/dashboard_builder.py` |
| **ServiceProvider**  | 기존 콜백 호환 브리지       | `services/service_provider.py`  |

### Single Responsibility 달성

- 각 서비스 = 1개 역할
- 테스트 용이성 향상
- 유지보수성 향상

## 모듈 구조

```
ugv_mon/
├── config.py             # 앱 설정 (패키지 루트)
├── constants.py          # 상수 (패키지 루트)
├── models.py             # 모델 (패키지 루트)
│
├── pipeline/             # 데이터 수집 파이프라인
│   ├── sniffer.py        # 패킷 캡처
│   ├── queue.py          # 패킷 큐
│   ├── processor.py      # 파싱 + 저장
│   └── icd_parser.py     # ICD 파싱
│
├── store/                # 데이터 저장소
│   └── packet_store.py   # 통합 저장 (deque)
│
├── services/             # 서비스 레이어
│   ├── capture_service.py
│   ├── stats_service.py
│   ├── ml_service.py
│   ├── dashboard_builder.py
│   └── service_provider.py
│
├── analysis/             # ML 분석
├── ui/                   # UI 모듈
│   ├── components/       # 재사용 컴포넌트
│   ├── layouts/          # 레이아웃
│   └── ml/               # ML 차트
├── callbacks/            # Dash 콜백
└── mock/                 # ⚠️ DEV ONLY
```

## PacketStore 설계

모든 통계/UI 데이터를 단일 deque에서 제공:

```python
PacketStore (deque[PacketRecord])
├── get_stats_dict()         → KPI 통계
├── get_jitter_p95()         → 지터 백분위
├── get_pps()                → 초당 패킷 수
├── get_availability()       → 가용성
├── get_logs()               → 로그 UI
├── get_chart_data()         → 차트 UI
├── get_connection_history() → 연결 이력
├── get_mode_transitions()   → 모드 전이
└── get_emergency_counts()   → 비상정지 통계
```

## 설계 결정

| 결정      | 선택             | 이유                     |
| --------- | ---------------- | ------------------------ |
| 갱신 방식 | Polling (2초)    | 단순성, 안정성           |
| 저장소    | 단일 deque       | 중복 제거, 유지보수 용이 |
| ML 모델   | Isolation Forest | 비지도 학습, 실시간 적용 |
| 아키텍처  | Service Layer    | SRP, 테스트 용이성       |
