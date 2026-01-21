# UGV-MON 파일 구조

## 디렉토리 구조

```
ugv_mon/
├── run.py                 # 앱 실행 진입점
├── requirements.txt       # 의존성 목록
│
└── ugv_mon/               # 메인 Python 패키지
    ├── app.py             # Dash 앱 팩토리
    ├── config.py          # 설정 관리
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
    │   ├── stats_calculator.py  # 지터, PPS, 가용성 계산
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
    │   └── log_table.py   # 로그 테이블
    │
    ├── layouts/           # 레이아웃
    │   ├── main_layout.py # 전체 레이아웃
    │   ├── header.py      # 헤더 바
    │   ├── panels.py      # 상태 패널들
    │   └── charts.py      # 차트
    │
    ├── callbacks/         # Dash 콜백
    │   └── update_callbacks.py  # 폴링 및 UI 업데이트
    │
    └── utils/             # 유틸리티
        └── helpers.py     # 색상, 스타일 헬퍼
```

## 핵심 파일 역할

| 파일 | 역할 |
|------|------|
| `run.py` | 앱 실행 (환경변수 기반 Mock/Live 전환) |
| `config.py` | 모든 설정 중앙 관리 |
| `capture/sniffer.py` | Scapy 패킷 캡처 (BPF 필터링) |
| `parser/icd_parser.py` | ICD v1.0 바이너리 파싱 |
| `data/live_provider.py` | 캡처+파싱 통합, UI 데이터 제공 |
| `callbacks/update_callbacks.py` | 2초 폴링 및 UI 갱신 |

## 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `UGV_MON_USE_LIVE` | `true`면 Live 모드 | Mock 모드 |
| `UGV_MON_INTERFACE` | 캡처 인터페이스 | `lo` |
| `UGV_MON_PORT` | 서버 포트 | `8050` |
| `UGV_MON_POLL_INTERVAL` | 폴링 간격 (ms) | `2000` |
