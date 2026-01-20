# UGV-MON 파일 구조 및 역할

> **마지막 업데이트**: 2026-01-20  
> **상태**: 최종 구현 완료

---

## 디렉토리 구조

```
opus1/
├── run.py                      # 앱 실행 진입점
├── requirements.txt            # 의존성 목록
│
├── ugv_mon/                    # 메인 Python 패키지
│   ├── __init__.py             # 패키지 초기화
│   ├── app.py                  # Dash 앱 팩토리
│   ├── config.py               # 설정 관리
│   │
│   ├── capture/                # 패킷 캡처 모듈 ✅
│   │   ├── __init__.py         # PacketSniffer, PacketQueue, CaptureStats export
│   │   ├── sniffer.py          # Scapy 기반 PacketSniffer
│   │   ├── queue.py            # 스레드 안전 PacketQueue
│   │   └── stats.py            # 캡처 통계 CaptureStats
│   │
│   ├── parser/                 # ICD 파싱 모듈 ✅
│   │   ├── __init__.py         # ICDParser, ParseResult 등 export
│   │   ├── models.py           # ICDHeader, StatusPayload, ParseResult
│   │   └── icd_parser.py       # 메인 파서 클래스
│   │
│   ├── analysis/               # 통계 분석 모듈 ✅
│   │   ├── __init__.py         # StatsCalculator, AnomalyDetector export
│   │   ├── stats_calculator.py # 지터, PPS, 가용성 계산
│   │   └── anomaly_detector.py # 이상 탐지
│   │
│   ├── data/                   # 데이터 모델 및 제공자
│   │   ├── __init__.py
│   │   ├── models.py           # 타입 정의 (Enum, dataclass)
│   │   ├── mock_data.py        # Mock 데이터 생성기
│   │   └── live_provider.py    # 실시간 데이터 제공자 ✅
│   │
│   ├── components/             # 재사용 UI 컴포넌트
│   │   ├── __init__.py
│   │   ├── status_chip.py      # 상태 칩 컴포넌트
│   │   ├── kpi_card.py         # KPI 카드
│   │   ├── device_grid.py      # 장치 연결 그리드
│   │   └── log_table.py        # AG-Grid 로그 테이블
│   │
│   ├── layouts/                # 레이아웃 구성
│   │   ├── __init__.py
│   │   ├── main_layout.py      # 전체 대시보드 조합
│   │   ├── header.py           # 헤더 바
│   │   ├── panels.py           # 상태/비상정지/장치 패널
│   │   └── charts.py           # Plotly 차트
│   │
│   ├── callbacks/              # Dash 콜백
│   │   ├── __init__.py
│   │   └── update_callbacks.py # 폴링 및 UI 업데이트
│   │
│   └── utils/                  # 유틸리티
│       ├── __init__.py
│       └── helpers.py          # 색상, 스타일 헬퍼
│
└── docs/                       # 문서
    ├── 00_PROJECT_OVERVIEW.md
    ├── 01_ARCHITECTURE.md
    ├── 02_FILE_STRUCTURE.md
    ├── 03_ICD_SPECIFICATION.md
    ├── 04_DAY01.md ~ 13_DAY10.md
    ├── CODE_ANALYSIS.md
    ├── CSU_DESIGN.md
    └── 99_APPENDIX.md
```

---

## 📄 파일별 상세 역할

### 루트 파일

#### `run.py` - 앱 진입점

- **역할**: 대시보드 서버 실행
- **기능**: 
  - 환경변수 기반 Mock/Live 모드 전환
  - 설정 정보 출력
  - 서버 실행 (Flask 개발 서버)
- **사용법**:
  ```bash
  # Mock 모드 (기본값)
  python run.py
  
  # Live 모드 (실시간 캡처)
  export UGV_MON_USE_LIVE=true
  sudo -E python run.py
  ```

#### `requirements.txt` - 의존성

- **핵심 패키지**:
  - `dash==2.14.2`
  - `dash-mantine-components==0.12.1`
  - `dash-ag-grid==31.0.1`
  - `plotly==5.18.0`
  - `scapy==2.5.0`

---

### `ugv_mon/capture/` - 패킷 캡처 모듈

#### `sniffer.py` - PacketSniffer 클래스

- **역할**: Scapy 기반 UDP 패킷 캡처
- **핵심 기능**:
  - BPF 필터링 (커널 레벨)
  - 별도 데몬 스레드에서 실행
  - 콜백 기반 패킷 전달
- **요구사항**: root 권한 또는 `cap_net_raw` capability

#### `queue.py` - PacketQueue 클래스

- **역할**: 스레드 안전 패킷 버퍼
- **패턴**: Producer-Consumer
- **특징**:
  - `deque(maxlen)` 기반 자동 메모리 관리
  - `get_all()`: 한 번에 모든 패킷 가져오기

#### `stats.py` - CaptureStats 클래스

- **역할**: 캡처 통계 추적
- **메트릭**: 총 패킷 수, PPS, 바이트 수, 필터 통과율

---

### `ugv_mon/parser/` - ICD 파싱 모듈

#### `icd_parser.py` - ICDParser 클래스

- **역할**: ICD v1.0 규격 패킷 파싱
- **기능**:
  - 체크섬 검증
  - 헤더 파싱 (12 bytes)
  - 상태보고(0x01) 페이로드 파싱
- **반환**: `ParseResult` 객체

#### `models.py` - 파싱 데이터 모델

- **클래스**:
  - `ICDHeader`: 헤더 필드
  - `StatusPayload`: 상태보고 페이로드
  - `ParseResult`: 파싱 결과 컨테이너

---

### `ugv_mon/analysis/` - 통계 분석 모듈

#### `stats_calculator.py` - StatsCalculator 클래스

- **역할**: 실시간 통계 계산
- **기능**:
  - 슬라이딩 윈도우 기반
  - PPS, 지터(P95/P99), 패킷 손실 계산
  - 가용성 계산

#### `anomaly_detector.py` - AnomalyDetector 클래스

- **역할**: 이상 탐지
- **탐지 대상**:
  - 높은 지터 (임계값 초과)
  - 패킷 손실 (시퀀스 갭)
  - 연결 타임아웃

---

### `ugv_mon/data/` - 데이터 모델

#### `models.py` - 타입 정의

- **Enum**:
  - `OperationMode`: 운용 모드
  - `Authority`: 운용 권한
  - `DrivingState`: 주행 상태
- **Dataclass**:
  - `DashboardState`: 대시보드 상태
  - `LogEntry`: 로그 엔트리
  - `DeviceStatus`: 장치 상태
  - `AvailabilitySegment`: 가용성 세그먼트
  - `EmergencyStatus`: 비상정지 상태

#### `mock_data.py` - MockDataGenerator 클래스

- **역할**: 시뮬레이션 데이터 생성 (개발/테스트용)
- **메서드**: 
  - `generate_initial_data()`: 초기 데이터
  - `update_data()`: 폴링 업데이트
  - `get_logs()`: 로그 조회

#### `live_provider.py` - LiveDataProvider 클래스

- **역할**: 실시간 데이터 제공 (캡처 + 파싱 통합)
- **인터페이스**: MockDataGenerator와 동일
- **팩토리 함수**: `get_data_provider()` - Mock/Live 자동 선택

---

### `ugv_mon/components/` - UI 컴포넌트

#### `status_chip.py`

- **역할**: 라벨-값 쌍 표시 칩
- **함수**: `create_status_chip(label, value, variant)`
- **Variant**: `success`, `warning`, `destructive`, `default`, `info`

#### `kpi_card.py`

- **역할**: KPI 메트릭 카드
- **함수**: 
  - `create_kpi_card()`: 단일 카드
  - `create_kpi_cards_row()`: 8개 카드 행

#### `device_grid.py`

- **역할**: 5x2 장치 연결 그리드
- **함수**: `create_device_grid(devices)`
- **기능**: 상태별 색상, hover tooltip

#### `log_table.py`

- **역할**: AG-Grid 로그 테이블
- **컬럼**: Time, Seq, Msg Code, Parse, Checksum, Mode, Authority, Notes
- **기능**: 정렬, 필터링, 조건부 스타일링

---

### `ugv_mon/layouts/` - 레이아웃

#### `main_layout.py`

- **역할**: 전체 대시보드 조합
- **dcc.Store 항목**:
  - `dashboard-data`: 대시보드 데이터
  - `is-paused`: 일시정지 상태
  - `chart-time-range`: 차트 시간 범위 (기본 60초)

#### `header.py`

- **역할**: 헤더 바
- **함수**: `create_status_chips()` - 상태 칩 리스트 생성

#### `panels.py`

- **역할**: 상태 패널들
- **패널**: 운용상태, 비상정지, 장치 연결

#### `charts.py`

- **역할**: Plotly 차트
- **함수**:
  - `create_communication_chart()`: PPS + 지터 통합 차트
  - `create_availability_timeline()`: 가용성 타임라인

---

### `ugv_mon/callbacks/` - 콜백

#### `update_callbacks.py`

- **역할**: 모든 대시보드 상호작용 처리
- **콜백**:
  1. `update_dashboard_data`: 2초마다 데이터 갱신
  2. `update_all_components`: UI 갱신
  3. `toggle_pause`: 일시정지 토글
  4. `update_time_range`: 시간 범위 변경
  5. `clear_logs`: 로그 초기화

---

### `ugv_mon/utils/` - 유틸리티

#### `helpers.py`

- **역할**: 공통 유틸리티 함수 (정리됨)
- **함수**:
  - `get_status_color()`: 상태별 색상 반환
  - `get_device_status_style()`: 장치 상태 스타일
  - `get_chart_colors()`: 차트 색상 팔레트

---

## 모듈 간 의존성

```
run.py
  └── ugv_mon/app.py
        ├── layouts/main_layout.py
        │     ├── layouts/header.py
        │     ├── layouts/panels.py
        │     └── layouts/charts.py
        ├── callbacks/update_callbacks.py
        │     ├── data/live_provider.py ← get_data_provider()
        │     │     ├── data/mock_data.py (Mock 모드)
        │     │     ├── capture/ (Live 모드)
        │     │     ├── parser/ (Live 모드)
        │     │     └── analysis/ (Live 모드)
        │     └── components/*.py
        └── config.py
              └── utils/helpers.py
```

---

## 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `UGV_MON_USE_LIVE` | `true`면 Live 모드 | (Mock 모드) |
| `UGV_MON_INTERFACE` | 캡처 인터페이스 | `lo` |
| `UGV_MON_PORT` | 서버 포트 | `8050` |
| `UGV_MON_POLL_INTERVAL` | 폴링 간격 (ms) | `2000` |

---

## 파일 생성 타임라인

| Day | 생성되는 파일 | 상태 |
|-----|--------------|------|
| Day 1 | `ugv_mon/` 기본 구조 | ✅ 완료 |
| Day 2 | `ugv_mon/capture/` 모듈 | ✅ 완료 |
| Day 3 | `ugv_mon/parser/` 모듈 | ✅ 완료 |
| Day 4 | `ugv_mon/data/live_provider.py` | ✅ 완료 |
| Day 5 | `ugv_mon/analysis/` 모듈 | ✅ 완료 |
| Day 6 | 실시간 데이터 연동 | ✅ 완료 |
| Day 7 | 안정화 (자동 재시작 등) | 문서 완료 |
| Day 8 | 차트 완성 | ✅ 완료 |
| Day 9 | 로그 테이블 완성 | ✅ 완료 |
| Day 10 | 최종 통합 테스트 | 문서 완료 |
