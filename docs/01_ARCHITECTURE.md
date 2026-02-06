# UGV-MON 아키텍처

> **최종 업데이트**: 2026-02-06

## 데이터 흐름

```
Network      ->    Capture    ->   Processor   ->    Store     ->    Provider   ->   Dashboard
Interface         +Queue          +Parser          (Single)       +Callbacks      UI
(lo/eno2)
    |               |               |               |               |              |
    v               v               v               v               v              v
UDP 패킷      Tuple 저장      파싱+저장        단일 deque      Dict(25키)      시각화
             (deque)        (ParseResult)   (PacketRecord)
```

## 모듈 구조

```
ugv_mon/
├── core/                 # 핵심 모듈
│   ├── models.py         # 통합 데이터 모델 (Enum, ICD, UI)
│   ├── config.py         # 앱 설정 (환경변수 기반)
│   └── constants.py      # 상수 정의 (장치ID, 포트 등)
│
├── capture/              # 패킷 캡처
│   ├── sniffer.py        # Scapy 스니퍼
│   ├── queue.py          # 스레드 안전 큐
│   ├── stats.py          # 캡처 카운터
│   └── packet_processor.py  # 처리 파이프라인 (queue->parser->store)
│
├── parser/               # ICD 파싱
│   └── icd_parser.py     # 메인 파서 (비트마스킹, 체크섬)
│
├── data/                 # 데이터 저장 및 제공
│   ├── packet_store.py   # 통합 저장소 (단일 deque)
│   ├── types.py          # DashboardData TypedDict (25키)
│   ├── live_provider.py  # 캡처 제어 + DashboardData 빌드
│   └── mock_data.py      # 테스트 데이터 생성기
│
├── components/           # UI 컴포넌트
├── layouts/              # 레이아웃 (panels.py, charts.py, header.py)
└── callbacks/            # Dash 콜백
```

## 책임 분리

```
packet_processor.py:     queue -> 언패킹 -> 파싱 -> 저장 (+ 이력 기록)
packet_store.py:         단일 deque 저장 + 통계/UI 데이터 제공
live_provider.py:        캡처 제어 + _build_dashboard_data() -> Dict(25키)
```

## 저장소 설계 (PacketStore)

```
packet_store.py:      deque[PacketRecord]  -> 모든 용도
                      ├── get_stats_dict()         -> KPI 통계
                      ├── get_jitter_p95()         -> 지터 백분위
                      ├── get_pps()                -> 초당 패킷 수
                      ├── get_logs()               -> 로그 UI
                      ├── get_chart_data()         -> 차트 UI
                      ├── get_stats_by_code()      -> msg_code별 통계
                      ├── get_connection_history()  -> 연결 이력
                      ├── get_mode_transitions()    -> 모드 전이 이력
                      └── get_emergency_counts()    -> 비상정지 통계
```

## 폴링 사이클

```
dcc.Interval (2초)
       |
       v
update_dashboard_data()
       |
       ├── processor.process_pending()     -> 패킷 처리
       |         |
       |         └── store.add()           -> 저장
       |
       └── provider._build_dashboard_data()  -> Dict(25키) 생성
              |
              ├── _build_connection_info()   -> 연결 정보 (5키)
              ├── _build_kpi_metrics()       -> KPI 지표 (8키)
              ├── _build_operational_info()   -> 운용 정보 (4키)
              └── _build_ui_display_data()   -> UI 데이터 (8키)
                     |
                     v
              dashboard-data Store 갱신
                     |
                     v
              UI 컴포넌트 갱신 (15개 Output)
```

## 설계 결정

### Polling vs WebSocket
- **선택**: Polling (dcc.Interval)
- **이유**: 단순성, 안정성, 2초 갱신으로 충분

### Mock vs Live 전환
- 동일한 인터페이스 제공 (다형성)
- 환경변수 또는 CLI 옵션으로 전환

### 단일 저장소 (PacketStore)
- **선택**: PacketStore (deque 1개)
- **이유**: 중복 제거, 단순화, 유지보수 용이
- **트레이드오프**: 읽기 시 변환 필요 (0.5ms, 무시 가능)

### dcc.Store("is-paused") 사용 근거
- 클라이언트(브라우저) 탭별 독립 UI 상태
- 서버 config/constants에 넣으면 모든 클라이언트가 공유하게 되어 부적합
- dcc.Store는 브라우저 세션 메모리(JS 변수)이며 DB가 아님
- 새로고침 시 초기값(False)으로 자동 리셋
- Dash 공식 권장 패턴
