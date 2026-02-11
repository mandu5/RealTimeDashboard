# UGV-MON 데이터 흐름 가이드

> **최종 업데이트**: 2026-02-08 (리팩터링 v2)

## 전체 데이터 흐름 (단방향)

```text
┌──────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────────┐
│ Network  │──▶│ Sniffer  │──▶│    Queue     │──▶│  Processor   │
│  (UDP)   │   │ (Scapy)  │   │ (deque)      │   │ (parse+add)  │
└──────────┘   └──────────┘   └──────────────┘   └──────┬───────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   PacketStore   │
                                               │ (deque 단일저장)│
                                               └────────┬────────┘
                                                        │
    ┌───────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Service Layer                                 │
├───────────────┬───────────────┬───────────────┬─────────────────┤
│ CaptureService│ StatsService  │  MLService    │DashboardBuilder │
│ (캡처 제어)   │ (통계 집계)   │ (이상 탐지)   │ (Dict 빌드)     │
└───────────────┴───────────────┴───────────────┴─────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │ ServiceProvider │
                            │ (오케스트레이터)│
                            └────────┬────────┘
                                     │
                                     ▼
                            ┌────────────────┐
                            │ UI Components  │
                            │  (11개 패널)   │
                            └────────────────┘
```

---

## 1. 파이프라인 계층 (Pipeline Layer)

### sniffer.py (`pipeline/sniffer.py`)

```python
def _capture_loop(self):
    # ...
    self._callback((datetime.now(), raw_data))  # Queue.put()으로 전달
```

**출력**: `Tuple[datetime, bytes]`

### queue.py (`pipeline/queue.py`)

```python
class PacketQueue:
    def put(self, packet: Tuple[datetime, bytes]):
        self._queue.append(packet)
```

---

## 2. 처리 계층 (Processing Layer)

### processor.py (`pipeline/processor.py`)

```python
class PacketProcessor:
    def process_pending(self) -> BatchProcessResult:
        for capture_time, packet_bytes in self._queue.get_all():
            result = self._parser.parse(packet_bytes)  # 파싱
            self._store.add(record)                    # 저장
        return BatchProcessResult(count, success_count, ...)
```

**역할**:

1. 큐에서 `(datetime, bytes)` 가져오기
2. **ICD 파서 호출** (파싱은 여기서만)
3. PacketRecord 생성 + 저장
4. BatchProcessResult 반환

---

## 3. 저장 계층 (Store Layer)

### packet_store.py (`store/packet_store.py`)

```python
class PacketStore:
    def add(self, record: PacketRecord):
        jitter = self._calculate_jitter(record)
        self._records.append(record)
```

**제공 메서드**:

- `get_pps()`, `get_jitter_p95()`, `get_availability()`
- `get_logs()`, `get_chart_data()`
- `get_connection_history()`, `get_mode_transitions()`

---

## 4. 서비스 계층 (Service Layer)

### CaptureService (`services/capture_service.py`)

```python
class CaptureService:
    """캡처 제어만 담당 (Single Responsibility)"""
    def start(self) -> bool    # Sniffer 생성 + 시작
    def stop(self) -> None     # Sniffer 정리
    def toggle(self) -> bool   # 시작/중지 토글
    def toggle_direction(self) -> str  # 포트 방향 전환
```

### StatsService (`services/stats_service.py`)

```python
class StatsService:
    """통계 카운터/연결 상태 관리"""
    def update(self, result: BatchProcessResult)
    def get_parse_rate() -> float
    def get_checksum_fail_rate() -> float
    def is_connected() -> bool  # 5초 타임아웃 체크
```

### MLService (`services/ml_service.py`)

```python
class MLService:
    """Rule+ML 앙상블 탐지"""
    def predict(self, store: PacketStore) -> dict
```

### DashboardBuilder (`services/dashboard_builder.py`)

```python
class DashboardBuilder:
    """Dict(25키) 빌드 (순수 함수)"""
    def build(self, is_connected, direction, ...) -> dict:
        return {
            **self._build_connection_info(),  # 5키
            **self._build_kpi_metrics(),      # 7키
            **self._build_operational_info(), # 4키
            **self._build_ui_display_data(),  # 7키
            "ml": ml_data,                    # 1키
        }
```

### ServiceProvider (`services/service_provider.py`)

```python
class ServiceProvider:
    """서비스 오케스트레이터 - 콜백 호환 브리지"""
    def update_data(self, prev_data) -> dict:
        result = self._processor.process_pending()  # 1. 패킷 처리
        self._stats.update(result)                  # 2. 통계 업데이트
        ml_data = self._ml.predict(self._store)     # 3. ML 예측
        return self._builder.build(...)             # 4. Dict 빌드

    # 콜백에서 호출하는 메서드들
    def start_capture(self) -> bool   # CaptureService.start() 호출
    def stop_capture() -> None        # CaptureService.stop() 호출
    def toggle_connection() -> bool   # 토글 + store/stats 리셋
```

---

## 5. 폴링 사이클 (2초)

```text
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

---

## 컴포넌트별 역할 비교

| 컴포넌트         | 역할             | 파싱  | 파일 위치                       |
| ---------------- | ---------------- | ----- | ------------------------------- |
| Sniffer          | 네트워크 캡처    | ✗     | `pipeline/sniffer.py`           |
| Queue            | 스레드 안전 버퍼 | ✗     | `pipeline/queue.py`             |
| **Processor**    | 파싱 + 저장      | **✓** | `pipeline/processor.py`         |
| Store            | 통계/이력 저장   | ✗     | `store/packet_store.py`         |
| CaptureService   | 캡처 제어        | ✗     | `services/capture_service.py`   |
| StatsService     | 통계 집계        | ✗     | `services/stats_service.py`     |
| MLService        | 이상 탐지        | ✗     | `services/ml_service.py`        |
| DashboardBuilder | Dict 빌드        | ✗     | `services/dashboard_builder.py` |

---

## CaptureService.start() vs ServiceProvider.start_capture()

| 메서드                            | 역할                                                          | 호출 위치            |
| --------------------------------- | ------------------------------------------------------------- | -------------------- |
| `CaptureService.start()`          | **단일 책임**: Sniffer 생성 및 시작만                         | ServiceProvider 내부 |
| `ServiceProvider.start_capture()` | **오케스트레이션**: CaptureService.start() 호출 + 추가 초기화 | Callbacks (UI)       |

**ServiceProvider**는 기존 `LiveDataProvider`를 대체하며, 4개 서비스를 조율하는 **Orchestrator/Facade** 역할입니다.
