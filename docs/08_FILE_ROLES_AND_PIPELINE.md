# UGV-MON 전체 파일 역할 및 데이터 파이프라인 상세 가이드

> **목적**: 프로젝트의 모든 파일이 파이프라인 어느 단계에서 어떤 역할을 하는지 이해하기 쉽게 정리

---

## 1. 파이프라인 전체 흐름 (단계별)

```text
[1단계] 네트워크     →  [2단계] 캡처      →  [3단계] 큐잉      →  [4단계] 파싱/저장
   UDP 패킷              Scapy BPF            스레드안전 deque      ICD 파서
                                                      │
                                                      ▼
[5단계] 저장소      ←────────────────────  PacketRecord 추가
   PacketStore
   (deque 기반)
        │
        ├── [6단계] 통계 집계 (StatsService)
        ├── [7단계] ML 예측 (MLService)
        └── [8단계] Dict 빌드 (DashboardBuilder)
                       │
                       ▼
              [9단계] ServiceProvider (오케스트레이션)
                       │
                       ▼
              [10단계] Dash 콜백 (2초 폴링)
                       │
                       ▼
              [11단계] UI 컴포넌트 렌더링
```

---

## 2. 진입점 및 설정

### `run.py` (프로젝트 루트)
- **역할**: CLI 진입점. Mock/Live 모드 선택, 환경변수 설정 후 `create_app()` 호출
- **파이프라인 단계**: 없음 (앱 부트스트랩 전)
- **주요 동작**: `argparse`로 `--mode`, `--interface`, `--port` 파싱 → `UGV_MON_USE_LIVE`, `UGV_MON_INTERFACE` 설정 → `create_app()` 실행

### `ugv_mon/app.py`
- **역할**: Dash 앱 팩토리. Mock/Live에 따라 DataProvider 선택, 레이아웃·콜백 등록
- **파이프라인 단계**: 9단계 이전 (초기 데이터 생성)
- **주요 동작**:
  - `UGV_MON_USE_LIVE=true` → `ServiceProvider` (Live)
  - 그 외 → `MockDataGenerator` (Mock)
  - `create_main_layout(initial_data, initial_logs)` → `register_callbacks(app, data_provider)`

### `ugv_mon/config.py`
- **역할**: 환경변수 기반 설정 (포트, 인터페이스, 폴링 간격, 타임아웃 등)
- **파이프라인 단계**: 전체 (설정 제공)
- **주요 클래스**: `AppConfig`, `NetworkConfig`, `UIConfig`, `ThresholdConfig`

### `ugv_mon/constants.py`
- **역할**: 장치 ID/이름, ICD 헤더 크기 등 상수
- **파이프라인 단계**: 4단계(파서), 8단계(빌더)에서 참조
- **주요 상수**: `DEVICE_IDS`, `DEVICE_NAMES`, `ICD_HEADER_SIZE`, `ICD_CHECKSUM_SIZE`, `ICD_MIN_PACKET_SIZE`

### `ugv_mon/models.py`
- **역할**: ICD 파싱용 Enum, 데이터클래스 (MsgCode, ICDHeader, ParseResult, OperationalPayload 등)
- **파이프라인 단계**: 4단계(파서), 8단계(빌더)에서 참조
- **주요 클래스**: `MsgCode`, `DeviceID`, `ICDHeader`, `OperationalPayload`, `ParseResult`

---

## 3. 1~4단계: 캡처 → 파싱 → 저장 (Pipeline Layer)

### `ugv_mon/pipeline/__init__.py`
- **역할**: `ICDParser`, `BatchProcessResult`, `PacketProcessor`, `PacketQueue`, `PacketSniffer` export
- **파이프라인 단계**: 2~4단계 모듈 통합

### `ugv_mon/pipeline/sniffer.py` — **2단계**
- **역할**: Scapy 기반 UDP 패킷 캡처. BPF 필터(VIC/OCS 포트) 적용
- **입력**: 네트워크 인터페이스, src/dst 포트
- **출력**: `(datetime, bytes)` 튜플 → `PacketQueue.put()` 콜백으로 전달
- **주요 클래스**: `PacketSniffer`

### `ugv_mon/pipeline/queue.py` — **3단계**
- **역할**: 스레드 안전 패킷 큐. Sniffer가 push, Processor가 pop
- **입력**: `(datetime, bytes)` 튜플
- **출력**: `get_all()`으로 배치 추출
- **주요 클래스**: `PacketQueue`

### `ugv_mon/pipeline/icd_parser.py` — **4단계 (파싱)**
- **역할**: ICD v1.0 규격 파싱. 헤더 12B + 체크섬 검증, 0x01 운용 상태 페이로드 해석
- **입력**: `bytes` (raw 패킷)
- **출력**: `ParseResult` (success, header, payload, checksum_ok, error)
- **주요 클래스**: `ICDParser`

### `ugv_mon/pipeline/processor.py` — **4단계 (조율)**
- **역할**: Queue → Parser → Store 연결. 배치 처리 후 `BatchProcessResult` 반환
- **입력**: `PacketQueue`, `PacketStore`, `ICDParser`
- **출력**: `BatchProcessResult` (count, success_count, checksum_fail_count 등)
- **주요 클래스**: `PacketProcessor`, `BatchProcessResult`

---

## 4. 5단계: 저장소 (Store Layer)

### `ugv_mon/store/packet_store.py` — **5단계**
- **역할**: 단일 deque에 `PacketRecord` 저장. 지터/패킷손실 계산, 통계/이력/차트용 데이터 제공
- **입력**: `PacketRecord` (processor에서 생성)
- **출력**:
  - 통계: `get_pps()`, `get_jitter_p95()`, `get_availability()`, `get_packet_loss()`, `get_parse_success_rate()`, `get_checksum_fail_rate()`, `get_stats_dict()`
  - UI: `get_logs()`, `get_chart_data()`, `get_connection_history()`, `get_mode_transitions()`, `get_emergency_counts()`
  - ML: `get_stats_history()`
- **주요 클래스**: `PacketRecord`, `PacketStore`

---

## 5. 6~8단계: 서비스 계층 (Service Layer)

### `ugv_mon/services/capture_service.py` — **6단계 (캡처 제어)**
- **역할**: Sniffer 시작/중지, 방향 전환(VIC→OCS / OCS→VIC). 통계/저장은 담당하지 않음
- **입력**: interface, queue, vic_port, ocs_port
- **출력**: `start()`, `stop()`, `toggle()`, `toggle_direction()`
- **주요 클래스**: `CaptureService`

### `ugv_mon/services/stats_service.py` — **6단계 (통계 집계)**
- **역할**: `BatchProcessResult` 집계, 파싱률/체크섬률 계산, 5초 타임아웃 기반 연결 상태 판단
- **입력**: `BatchProcessResult` (processor에서)
- **출력**: `get_parse_rate()`, `get_checksum_fail_rate()`, `is_connected()`, `last_packet_time_str`, `last_payload`
- **주요 클래스**: `StatsService`, `StatsSnapshot`

### `ugv_mon/services/ml_service.py` — **7단계**
- **역할**: Rule + ML 앙상블 이상 탐지. `PacketStore`에서 통계 추출 → `MLPipeline`/`RuleDetector` 호출
- **입력**: `PacketStore` (get_stats_dict, get_parse_success_rate 등)
- **출력**: `{ is_anomaly, anomaly_score, confidence, contributing_features, records, score_history, ... }`
- **주요 클래스**: `MLService`

### `ugv_mon/services/dashboard_builder.py` — **8단계**
- **역할**: Store + Stats + ML 결과를 조합해 대시보드용 Dict 빌드
- **입력**: Store, Stats, is_connected, direction, filter_str, interface, ml_data
- **출력**: 연결정보(5키) + KPI(7키) + 운용정보(4키) + UI데이터(combinedData, devices, connectionHistory, modeTransitions, emergencyCounts) + ml
- **주요 클래스**: `DashboardBuilder`

### `ugv_mon/services/service_provider.py` — **9단계 (오케스트레이터)**
- **역할**: Live 모드 시 4개 서비스 조율. `DataProviderProtocol` 구현 → 콜백 호환
- **입력**: interface
- **출력**: `update_data()`, `generate_initial_data()`, `get_logs()`, `clear_logs()`, `start_capture()`, `stop_capture()`, `toggle_connection()`, `toggle_direction()`
- **주요 클래스**: `ServiceProvider`

---

## 6. ML 분석 모듈 (7단계 내부)

### `ugv_mon/analysis/feature_extractor.py`
- **역할**: 통계 dict → ML 특성 벡터 변환 (jitter_current, jitter_p95, pps_trend, loss_rate, quality_score 등)
- **파이프라인 단계**: 7단계 (MLService 내부)
- **주요 클래스**: `FeatureExtractor`, `FeatureVector`

### `ugv_mon/analysis/ml_anomaly_detector.py`
- **역할**: Isolation Forest 기반 비지도 이상 탐지. fit/predict, 모델 저장/로드
- **파이프라인 단계**: 7단계 (MLPipeline 내부)
- **주요 클래스**: `MLAnomalyDetector`, `AnomalyResult`

### `ugv_mon/analysis/rule_detector.py`
- **역할**: 규칙 기반 탐지 (PPS 급락, 가용성 저하 등). Cold Start 대응
- **파이프라인 단계**: 7단계 (MLService 내부)
- **주요 클래스**: `RuleDetector`, `RuleResult`

### `ugv_mon/analysis/ml_pipeline.py`
- **역할**: FeatureExtractor + MLAnomalyDetector 조율. 학습/예측/캐싱
- **파이프라인 단계**: 7단계 (MLService에서 사용)
- **주요 클래스**: `MLPipeline`

---

## 7. 10~11단계: 콜백 및 UI

### `ugv_mon/callbacks/update_callbacks.py` — **10단계**
- **역할**: Dash 콜백 등록. 2초 폴링 → `update_data()` → Output 갱신
- **주요 콜백**:
  - `update_data`: `dashboard-data` 갱신
  - `update_main_components`: status-chips, kpi-cards, operational-status, device-grid, comm-quality-chart, 로그/이력/비상정지 패널 등
  - `toggle_pause`, `clear_logs`, `on_connection_toggle`, `on_direction_toggle`, `update_ml_panel`
- **파이프라인 단계**: 9단계 ServiceProvider와 연동

### `ugv_mon/ui/layouts/main_layout.py` — **11단계 (레이아웃)**
- **역할**: 전체 페이지 구조. dcc.Store, dcc.Interval, 헤더, KPI, 메인 콘텐츠, 로그 패널
- **주요 함수**: `create_main_layout(initial_data, initial_logs)`

### `ugv_mon/ui/layouts/header.py`
- **역할**: 상단 헤더 바 (연결 상태 칩, 방향 버튼)
- **주요 함수**: `create_header_bar(data)`, `create_status_chips(data)`

### `ugv_mon/ui/layouts/panels.py`
- **역할**: 11개 패널 정의 (운용상태, 비상정지, 장치, 통신품질차트, 연결이력, 모드전이, 비상정지통계, 로그, ML분석)
- **주요 함수**: `create_operational_status_panel`, `create_emergency_status_panel`, `create_device_panel`, `create_charts_panel`, `create_connection_history_panel`, `create_mode_transitions_panel`, `create_emergency_stats_panel`, `create_log_panel`, `create_ml_analysis_panel`

### `ugv_mon/ui/layouts/charts.py`
- **역할**: Plotly PPS+지터 듀얼 Y축 차트
- **주요 함수**: `create_communication_chart(data, p95, time_range_seconds)`

### `ugv_mon/ui/layouts/ml_charts.py`
- **역할**: ML 시각화 re-export (panels에서 import 편의)
- **내용**: `create_anomaly_3d_scatter`, `create_anomaly_timeline`, `create_confidence_gauge`, `create_feature_contribution_chart` export

### `ugv_mon/ui/components/kpi_card.py`
- **역할**: 7개 KPI 카드 (수신 PPS, 파싱성공률, 체크섬오류율, 패킷손실, 가용성, 지터 현재/P95)
- **주요 함수**: `create_kpi_card()`, `create_kpi_cards_row(data)`

### `ugv_mon/ui/components/device_grid.py`
- **역할**: 10개 장치 연결 상태 그리드
- **주요 함수**: `create_device_grid(devices)`

### `ugv_mon/ui/components/status_chip.py`
- **역할**: 연결 상태 칩 (연결됨/끊김, 인터페이스 등)
- **주요 함수**: `create_status_chip()`, `create_status_chips(data)`

### `ugv_mon/ui/components/log_table.py`
- **역할**: AG-Grid 기반 로그 테이블 (timestamp, sequence, msg_code, parse_ok, checksum_ok, mode, authority, error)
- **주요 함수**: `get_log_column_defs()`, `create_log_table()`, `create_log_table_header()`, `filter_logs()`

### `ugv_mon/ui/ml/anomaly_3d.py`
- **역할**: 3D 이상 탐지 산점도 (지터, PPS, 손실률)
- **주요 함수**: `create_anomaly_3d_scatter(records, anomaly_scores, threshold)`

### `ugv_mon/ui/ml/anomaly_timeline.py`
- **역할**: 이상 점수 타임라인, 신뢰도 게이지
- **주요 함수**: `create_anomaly_timeline(score_history)`, `create_confidence_gauge(confidence)`

### `ugv_mon/ui/ml/feature_importance.py`
- **역할**: 기여 특성 Z-Score 바 차트
- **주요 함수**: `create_feature_contribution_chart(contributing_features)`

### `ugv_mon/styles.py`
- **역할**: UI 스타일 상수 (색상, 레이아웃, 차트 색상)
- **주요 내용**: `COLORS`, `FLEX_COLUMN`, `KPI_GRID`, `get_chart_colors()` 등

---

## 8. Mock 모드 전용

### `ugv_mon/mock/mock_data.py`
- **역할**: 테스트/개발용 가짜 데이터 생성. `DataProviderProtocol` 구현
- **파이프라인 단계**: 9단계 대체 (Live 대신 Mock)
- **주요 클래스**: `MockDataGenerator`

---

## 9. 테스트 및 기타

### `tests/test_icd_parser.py`
- **역할**: ICD 파서 단위 테스트

### `tests/test_packet_store.py`
- **역할**: PacketStore 단위 테스트 (add, jitter, packet_loss, 통계, 이력)

### `tests/test_ml_anomaly_detector.py`
- **역할**: FeatureExtractor, MLAnomalyDetector, MLPipeline 테스트

### `requirements.txt`
- **역할**: 의존성 목록 (dash, plotly, scapy, scikit-learn, numpy, pytest)

### `pyproject.toml`
- **역할**: mypy, pytest, coverage 설정
