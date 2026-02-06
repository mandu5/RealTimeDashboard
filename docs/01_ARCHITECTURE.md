# UGV-MON 아키텍처

> **최종 업데이트**: 2026-02-04

## 데이터 흐름

```
Network      →    Capture    →   Processor   →    Store     →    Provider   →   Dashboard
Interface         +Queue          +Parser          (Single)       +Callbacks      UI
(lo/eno2)                                                    
    │               │               │               │               │              │
    ▼               ▼               ▼               ▼               ▼              ▼
UDP 패킷      Tuple 저장      파싱+통계       단일 deque      Dict(25키)      시각화
             (deque)        (ParseResult)   (PacketRecord)                    
```

## 모듈 구조 (2026-02-04 개선)

```
ugv_mon/
├── capture/              # 패킷 캡처
│   ├── sniffer.py        # Scapy 스니퍼
│   ├── queue.py          # 스레드 안전 큐
│   ├── stats.py          # 캡처 카운터
│   └── packet_processor.py  # ★ 처리 파이프라인 (NEW)
│
├── parser/               # ICD 파싱
│   ├── icd_parser.py     # 메인 파서
│   └── models.py         # 데이터 모델
│
├── data/                 # 데이터 저장 및 제공
│   ├── packet_store.py   # ★ 통합 저장소 (NEW)
│   ├── types.py          # ★ TypedDict 정의 (NEW)
│   ├── live_provider.py  # 대시보드 데이터 제공
│   └── mock_data.py      # 테스트 데이터
│
├── analysis/             # 분석 (하위호환)
│   └── stats_calculator.py
│
├── components/           # UI 컴포넌트
├── layouts/              # 레이아웃
└── callbacks/            # Dash 콜백
```

## 책임 분리 (개선됨)

### Before
```
live_provider.py (6가지 책임):
├── queue 접근
├── Tuple 언패킹
├── parser 호출
├── stats_calc 호출
├── deque 5개 저장
└── Dict 생성
```

### After
```
packet_processor.py:     queue → 언패킹 → 파싱 → 저장
packet_store.py:         단일 deque 저장 + 통계/UI 데이터 제공
live_provider.py:        캡처 제어 + Dict 생성
```

## 저장소 통합

### Before (중복)
```
stats_calculator.py:  List[Dict]     → 통계용
live_provider.py:     deque × 5개    → UI용
                      (로그, 차트, 연결이력, 모드전이, 비상통계)
```

### After (단일)
```
packet_store.py:      deque[PacketRecord]  → 모든 용도
                      ├── get_stats_dict()      → 통계
                      ├── get_logs()            → 로그 UI
                      ├── get_chart_data()      → 차트 UI
                      └── get_connection_history() → 이력 UI
```

## 폴링 사이클

```
dcc.Interval (2초)
       │
       ▼
update_dashboard_data()
       │
       ├── processor.process_pending()  → 패킷 처리
       │         │
       │         └── store.add()        → 저장
       │
       └── provider._build_state()      → Dict(25키) 생성
              │
              └── store.get_*()         → 데이터 조회
                     │
                     ▼
              dashboard-data Store 갱신
                     │
                     ▼
              UI 컴포넌트 갱신
```

## 설계 결정

### Polling vs WebSocket
- **선택**: Polling (dcc.Interval)
- **이유**: 단순성, 안정성, 2초 갱신으로 충분

### Mock vs Live 전환
- 동일한 인터페이스 제공 (다형성)
- 환경변수로 전환: `UGV_MON_USE_LIVE=true`

### 단일 저장소 (2026-02-04)
- **선택**: PacketStore (deque 1개)
- **이유**: 중복 제거, 단순화, 유지보수 용이
- **트레이드오프**: 읽기 시 변환 필요 (0.5ms, 무시 가능)
