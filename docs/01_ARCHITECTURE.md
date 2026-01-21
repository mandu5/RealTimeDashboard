# UGV-MON 아키텍처

## 데이터 흐름

```
Network      →    Scapy     →    ICD      →   Analysis   →    Dash
Interface         Capture        Parser       Module          Dashboard
(lo/eno2)         +Filter                                    
    │                │              │             │              │
    ▼                ▼              ▼             ▼              ▼
UDP 패킷       필터링된        파싱된 상태     분석 결과      시각화 UI
             패킷 스트림     (모드/권한/    (KPI/지터/
                            장치/비상)     가용성)
```

## 모듈 구조

```
ugv_mon/
├── capture/        # 패킷 캡처
│   ├── sniffer.py  # Scapy 스니퍼
│   ├── queue.py    # 스레드 안전 큐
│   └── stats.py    # 캡처 통계
│
├── parser/         # ICD 파싱
│   ├── icd_parser.py   # 메인 파서
│   └── models.py       # 데이터 모델
│
├── analysis/       # 통계 분석
│   ├── stats_calculator.py  # 지터/PPS/가용성
│   └── anomaly_detector.py  # 이상 탐지
│
├── data/           # 데이터 제공
│   ├── live_provider.py  # 실시간 데이터
│   ├── mock_data.py      # 테스트 데이터
│   └── models.py         # 타입 정의
│
├── components/     # UI 컴포넌트
├── layouts/        # 레이아웃
└── callbacks/      # Dash 콜백
```

## 폴링 사이클

```
dcc.Interval (2초)
       │
       ▼
update_dashboard_data()  ─→  dashboard-data Store 갱신
       │
       ▼
update_all_components()  ─→  UI 컴포넌트 갱신
```

## 설계 결정

### Polling vs WebSocket
- **선택**: Polling (dcc.Interval)
- **이유**: 단순성, 안정성, 2초 갱신으로 충분

### Mock vs Live 전환
- 동일한 인터페이스 제공 (다형성)
- 환경변수로 전환: `UGV_MON_USE_LIVE=true`
