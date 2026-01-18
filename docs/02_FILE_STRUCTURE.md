# UGV-MON 파일 구조 및 역할

---

## 디렉토리 구조

```
opus1/
├── run.py                      # 앱 실행
├── requirements.txt            # 의존성 목록
│
├── ugv_mon/                    # 메인 Python 패키지
│   ├── __init__.py             # 패키지 초기화
│   ├── app.py                  # Dash 앱 팩토리
│   ├── config.py               # 설정 관리
│   │
│   ├── components/             # 재사용 UI 컴포넌트
│   │   ├── status_chip.py      # 헤더 상태 섹션
│   │   ├── kpi_card.py         # KPI 카드
│   │   ├── device_grid.py      # 장치 연결 상태
│   │   └── log_table.py        # AG-Grid 로그 테이블
│   │
│   ├── layouts/                # 레이아웃 구성
│   │   ├── main_layout.py      # 전체 대시보드 조합
│   │   ├── header.py           # 헤더 바
│   │   ├── panels.py           # 상태/비상정지/장치 패널
│   │   └── charts.py           # Plotly 차트
│   │
│   ├── callbacks/              # Dash 콜백
│   │   └── update_callbacks.py # 폴링 및 UI 업데이트
│   │
│   ├── data/                   # 데이터 모델
│   │   ├── models.py           # 타입 정의 (Enum, dataclass)
│   │   └── mock_data.py        # 목 데이터 생성기
│   │
│   ├── capture/                # 패킷 캡처 (Day 2)
│   │   ├── __init__.py
│   │   ├── sniffer.py          # Scapy 스니퍼
│   │   └── filter.py           # BPF 필터
│   │
│   ├── parser/                 # ICD 파싱 (Day 3)
│   │   ├── __init__.py
│   │   ├── icd_parser.py       # 메인 파서
│   │   ├── header.py           # 헤더 파싱
│   │   ├── payload.py          # 페이로드 파싱
│   │   └── checksum.py         # 체크섬 검증
│   │
│   ├── analysis/               # 데이터 분석 (Day 4-6)
│   │   ├── __init__.py
│   │   ├── quality.py          # 품질 분석
│   │   ├── availability.py     # 가용성 분석
│   │   ├── jitter.py           # 지터 분석
│   │   └── loss.py             # 손실 추정
│   │
│   └── utils/                  # 유틸리티
│       └── helpers.py          # 색상, 포맷팅, 변환 함수
│
└── docs/                       # 문서
    ├── 00_PROJECT_OVERVIEW.md
    ├── 01_ARCHITECTURE.md
    ├── 02_FILE_STRUCTURE.md
    ├── 03_ICD_SPECIFICATION.md
    ├── 04_DAY01.md ~ 13_DAY10.md
    └── 99_APPENDIX.md
```

---

## 📄 파일별 상세 역할

### 루트 파일

#### `run.py` - 앱 진입점
- **역할**: `python run.py`로 대시보드 실행
- **기능**: 
  - 환경변수 읽기
  - `ugv_mon.app.create_app()` 호출
  - 서버 실행 (Flask 개발 서버)
- **사용법**:
  ```bash
  sudo python run.py
  UGV_MON_PORT=8080 sudo python run.py
  ```

#### `requirements.txt` - 의존성
- **핵심 패키지**:
  - `dash`, `dash-mantine-components`, `dash-ag-grid`
  - `plotly`, `pandas`, `numpy`
  - `scapy` (Day 2 이후)

---

### `ugv_mon/` 패키지

#### `ugv_mon/app.py` - Dash 앱 팩토리
- **역할**: Dash 앱 인스턴스 생성 및 설정
- **구현 내용**:
  1. 외부 스타일시트 설정 (Inter 폰트)
  2. 초기 데이터 생성 (`MockDataGenerator`)
  3. 레이아웃 설정 (`create_main_layout`)
  4. 콜백 등록 (`register_callbacks`)
- **반환**: 설정된 Dash 앱 인스턴스

#### `ugv_mon/config.py` - 설정 관리
- **역할**: 모든 설정을 중앙 관리 (dataclass 기반)
- **섹션**:
  - `AppConfig`: 서버 호스트/포트/디버그
  - `NetworkConfig`: 인터페이스, UDP 포트
  - `UIConfig`: 폴링 주기, 버퍼 크기
  - `ThresholdConfig`: 경고 임계값
  - `ICDConfig`: ICD 파싱 오프셋/크기
  - `DeviceConfig`: 10개 장치 목록

---

### `ugv_mon/components/` - UI 컴포넌트

#### `status_chip.py`
- **역할**: 라벨-값 쌍 표시 칩
- **사용 위치**: 헤더 바 (연결상태, 인터페이스, 필터)
- **함수**: `create_status_chip(label, value, variant)`
- **Variant**: `success`, `warning`, `destructive`, `default`, `info`

#### `kpi_card.py`
- **역할**: KPI 메트릭 카드
- **사용 위치**: KPI 행 (8개 카드)
- **함수**: 
  - `create_kpi_card()`: 단일 카드
  - `create_kpi_cards_row()`: 8개 카드 행
- **표시 메트릭**: pps, 필터통과율, 파싱성공률, 체크섬오류율, 패킷손실, 가용성(5분/1시간), 지터(P95/P99)

#### `device_grid.py`
- **역할**: 5x2 장치 연결 그리드
- **사용 위치**: 장치 연결 상태 패널
- **함수**: `create_device_grid(devices)`
- **장치**: VIC, RDC, ADC, FCAM, RCAM, AUX, SCS, DIP, TCC, TM (10개)

#### `log_table.py`
- **역할**: AG-Grid 로그 테이블
- **사용 위치**: 하단 로그/이벤트 영역
- **컬럼**: Time, Seq, Msg Code, Parse, Checksum, Mode, Authority, Notes
- **기능**: 정렬, 필터링, 조건부 스타일링

---

### `ugv_mon/layouts/` - 레이아웃

#### `main_layout.py`
- **역할**: 전체 대시보드 조합
- **구성 요소**:
  - `dcc.Store`: 상태 저장소
  - `dcc.Interval`: 폴링 주기
  - 헤더 바, KPI 카드 행, 메인 콘텐츠, 로그 테이블

#### `header.py`
- **역할**: 헤더 바
- **내용**: 제목, 상태 칩 4개 (연결상태, 인터페이스, 필터, 마지막 패킷)

#### `panels.py`
- **역할**: 상태 패널들
- **패널**:
  - 운용상태: 운용모드/권한/주행상태
  - 비상정지: 10개 원인 인디케이터
  - 장치: 10개 장치 연결 그리드

#### `charts.py`
- **역할**: Plotly 차트
- **차트**:
  - `create_communication_chart()`: PPS + 지터 (스택)
  - `create_availability_timeline()`: 가용성 타임라인

---

### `ugv_mon/callbacks/` - 콜백

#### `update_callbacks.py`
- **역할**: 모든 대시보드 상호작용 처리
- **콜백 3종류**:
  1. `update_dashboard_data`: 2초마다 데이터 갱신
  2. `update_all_components`: 데이터 변경 시 UI 갱신
  3. 컨트롤 콜백: Pause/Resume, Auto-scroll, Clear

---

### `ugv_mon/data/` - 데이터 모델

#### `models.py`
- **역할**: 타입 정의 (Enum, dataclass)
- **핵심 클래스**:
  - `OperationMode`, `Authority`, `DrivingState` (Enum)
  - `DashboardState`, `LogEntry`, `DeviceStatus` (dataclass)

#### `mock_data.py`
- **역할**: 목 데이터 생성기 (Day 2-3에서 실제 캡처로 대체)
- **클래스**: `MockDataGenerator`
- **메서드**: 
  - `generate_initial_data()`: 초기 데이터
  - `update_data()`: 폴링 업데이트

---

### `ugv_mon/utils/` - 유틸리티

#### `helpers.py`
- **역할**: 공통 유틸리티 함수
- **함수 목록**:
  - `get_status_color()`: 상태별 색상 반환
  - `get_device_status_style()`: 장치 상태 스타일
  - `get_chart_colors()`: 차트 색상 팔레트
  - `format_percentage()`: 퍼센트 포맷팅
  - `format_timestamp()`: 시간 포맷팅
  - `get_operation_mode_label()`: 운용모드 비트 → 한글 라벨
  - `get_authority_label()`: 권한 비트 → 한글 라벨
  - `get_driving_state_label()`: 주행상태 비트 → 한글 라벨
  - `seq_gap_with_rollover()`: 시퀀스 갭 계산 (롤오버 처리)

---

## 모듈 간 의존성

```
app.py
  ├── layouts/main_layout.py
  │     ├── layouts/header.py
  │     ├── layouts/panels.py
  │     └── layouts/charts.py
  ├── callbacks/update_callbacks.py
  │     ├── data/mock_data.py (Day 1-6)
  │     ├── data/live_data.py (Day 7-10)
  │     └── components/*.py
  └── config.py
        └── utils/helpers.py
```

---

## 파일 생성 타임라인

| Day | 생성되는 파일 |
|-----|--------------|
| Day 1 | `ugv_mon/` 전체 기본 구조 ✅ |
| Day 2 | `ugv_mon/capture/` 모듈 |
| Day 3 | `ugv_mon/parser/` 모듈 |
| Day 4 | `ugv_mon/analysis/quality.py` |
| Day 5 | `ugv_mon/analysis/availability.py` |
| Day 6 | `ugv_mon/analysis/jitter.py`, `loss.py` |
| Day 7 | `ugv_mon/data/live_data.py` |
| Day 10 | `tests/` 디렉토리 |
