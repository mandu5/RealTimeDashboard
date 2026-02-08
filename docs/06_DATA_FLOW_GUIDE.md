# UGV-MON 데이터 흐름 가이드

> **최종 업데이트**: 2026-02-08

## 전체 데이터 흐름

```text
┌──────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────────┐
│ Network  │──▶│ Sniffer  │──▶│    Queue     │──▶│  Processor   │
│  (UDP)   │   │ (Scapy)  │   │ (deque)      │   │ (parse+add)  │
└──────────┘   └──────────┘   └──────────────┘   └──────┬───────┘
                                                        │
              ┌─────────────────────────────────────────┘
              ▼
┌──────────────────┐   ┌──────────────────────────────────────────┐
│   PacketStore    │◀──│           LiveDataProvider               │
│ (deque 단일저장) │   │  (Facade + Orchestrator 패턴)            │
└────────┬─────────┘   │  - 캡처 컴포넌트 초기화/제어              │
         │              │  - 상태 관리 (연결, 카운터)              │
         │              │  - 가용성 세그먼트 계산                  │
         └─────────────▶│  - Dict(25키) 빌드                      │
                        └────────────────────┬─────────────────────┘
                                             │
                                             ▼
                                   ┌────────────────┐
                                   │  UI Components │
                                   │  (12개 패널)    │
                                   └────────────────┘
```

---

## 1. 캡처 계층 (Capture Layer)

### sniffer.py

```python
# Scapy BPF 필터로 UDP 패킷 캡처
def _process_packet(self, packet):
    capture_time = datetime.now()
    raw_data = bytes(packet[Raw].load)
    self._callback((capture_time, raw_data))  # Queue로 전달
```

**출력**: `Tuple[datetime, bytes]`

### queue.py

```python
# 스레드 안전 deque 저장
class PacketQueue:
    def push(self, packet: Tuple[datetime, bytes]):
        with self._lock:
            self._queue.append(packet)
```

---

## 2. 처리 계층 (Processing Layer)

### packet_processor.py

```python
class PacketProcessor:
    def __init__(self, queue, parser, store):
        self._queue = queue
        self._parser = parser  # ICD 파서 (여기서만 호출)
        self._store = store

    def process_pending(self) -> BatchProcessResult:
        for capture_time, packet_bytes in self._queue.get_all():
            result = self._parser.parse(packet_bytes)  # 파싱
            record = PacketRecord(...)
            self._store.add(record)                    # 저장
        return BatchProcessResult(count, success_count, ...)
```

**역할**:

1. 큐에서 `(datetime, bytes)` 가져오기
2. **ICD 파서 호출** (파싱은 여기서만)
3. PacketRecord 생성 + 저장
4. BatchProcessResult 반환 (집계 결과)

---

## 3. 저장 계층 (Data Layer)

### packet_store.py

```python
class PacketStore:
    def __init__(self, window_sec: int = 3600):
        self._records: deque[PacketRecord] = deque(maxlen=360000)

    def add(self, record: PacketRecord) -> Optional[float]:
        jitter = self._calculate_jitter(record)
        record.jitter_ms = jitter
        self._records.append(record)
        return jitter
```

**제공 메서드**:

- `get_pps()`, `get_jitter_p95()`, `get_availability()`
- `get_packet_loss()`, `get_logs()`, `get_chart_data()`
- `get_connection_history()`, `get_mode_transitions()`

---

## 4. 조율자 계층 (LiveDataProvider - Facade + Orchestrator)

> ⚠️ **LiveDataProvider는 단순 Dict 빌더가 아닙니다!**  
> 전체 캡처 시스템의 **Facade + Orchestrator** 역할을 합니다.

### 역할 1: 캡처 컴포넌트 초기화 및 제어

```python
class LiveDataProvider:
    def __init__(self, interface):
        # 모든 컴포넌트 생성 및 연결
        self._packet_queue = PacketQueue()
        self._parser = ICDParser()
        self._store = PacketStore()
        self._processor = PacketProcessor(queue, parser, store)
        self._ml_pipeline = MLPipeline()

    def start_capture(self):
        self._sniffer = PacketSniffer(...)
        self._sniffer.start()

    def stop_capture(self):
        self._sniffer.stop()

    def toggle_direction(self):
        # 상태→제어 또는 제어→상태 방향 전환
```

### 역할 2: 상태 관리 및 집계

```python
def update_data(self, prev_data):
    # 1. Processor 호출 (파싱 수행)
    result = self._processor.process_pending()

    # 2. 자체 카운터 집계 (Processor 결과 누적)
    self._total_packets += result.count
    self._parse_success += result.success_count
    self._checksum_fail += result.checksum_fail_count

    # 3. 마지막 payload 저장 (운용 정보용)
    if result.last_payload:
        self._last_payload = result.last_payload

    # 4. 연결 타임아웃 체크
    self._check_connection_timeout()

    # 5. 가용성 세그먼트 기록 (회사 방식)
    self._record_uptime_segment(self._is_connected)
```

### 역할 3: 가용성 세그먼트 계산 (회사 방식)

```python
def _record_uptime_segment(self, new_is_up):
    # 연결/끊김 구간을 시간대별로 기록
    # 가용성 타임라인 차트용
```

### 역할 4: Dict(25키) 빌드

```python
def _build_dashboard_data(self) -> dict:
    return {
        **self._build_connection_info(),      # 5키 (자체 상태)
        **self._build_kpi_metrics(),          # 8키 (Store + 자체 카운터)
        **self._build_operational_info(),     # 4키 (last_payload)
        **self._build_ui_display_data(),      # 7키 (Store + 자체)
        "ml": self._build_ml_data(),          # 1키 (ML 파이프라인)
    }
```

**KPI 지표 빌드 예시**:

```python
def _build_kpi_metrics(self):
    stats = self._store.get_stats_dict()  # Store에서 가져오기
    return {
        "capturePps": stats.get("pps", 0),  # Store
        # 자체 카운터로 계산
        "parseSuccess": (self._parse_success / self._total_packets) * 100,
        "checksumFail": (self._checksum_fail / self._total_packets) * 100,
        "availability": stats.get("availability", 0.0),  # Store
    }
```

---

## 5. 프레젠테이션 계층 (Callbacks)

### update_callbacks.py

```python
@callback(Output("dashboard-data", "data"), ...)
def update_dashboard_data(n, is_paused):
    return provider.update_data(prev_data)  # LiveProvider 호출

@callback([15개 Output], Input("dashboard-data", "data"))
def update_main_components(data):
    # Dict → UI 컴포넌트 변환
```

---

## 폴링 사이클 상세 (2초)

```text
dcc.Interval (2초)
     │
     ▼
update_dashboard_data()
     │
     └── provider.update_data()
              │
              ├── 1. processor.process_pending()
              │        ├── queue.get_all()
              │        ├── parser.parse()  ← 파싱은 여기서만!
              │        └── store.add()
              │
              ├── 2. 자체 카운터 집계
              │        (total_packets, parse_success, checksum_fail)
              │
              ├── 3. 연결 타임아웃 체크
              │
              ├── 4. 가용성 세그먼트 기록
              │
              └── 5. _build_dashboard_data()
                       ├── Store에서 데이터
                       ├── 자체 카운터로 비율 계산
                       ├── last_payload로 운용 정보
                       └── Dict(25키) 반환
                              │
                              ▼
                       dcc.Store 갱신 → UI 업데이트
```

---

## LiveProvider vs 다른 컴포넌트

| 컴포넌트         | 역할                    | 파싱 여부          |
| ---------------- | ----------------------- | ------------------ |
| **Sniffer**      | 네트워크에서 bytes 캡처 | ✗                  |
| **Queue**        | 스레드 안전 버퍼        | ✗                  |
| **Processor**    | 파싱 + 저장             | **✓ (여기서만)**   |
| **Store**        | 통계/이력 저장          | ✗                  |
| **LiveProvider** | **전체 조율 (Facade)**  | ✗ (Processor 호출) |

---

## 왜 LiveProvider가 복잡한가?

1. **중앙 집중 제어**: 모든 컴포넌트 생명주기 관리
2. **상태 집계**: Processor 결과를 Provider 레벨에서 누적
3. **두 가지 데이터 소스**: Store 통계 + 자체 카운터 조합
4. **회사 방식 구현**: 가용성 세그먼트 별도 로직
5. **ML 통합**: 파이프라인 초기화 및 조율
