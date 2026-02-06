# UGV-MON 데이터 흐름 상세 가이드

> **최종 수정**: 2026-02-04  
> **목적**: 시스템 전체 데이터 흐름 및 각 모듈의 역할 이해

---

## 1. 전체 데이터 흐름 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              네트워크 레이어                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  UGV (무인차량) ──UDP 패킷──▶ 네트워크 인터페이스 (eno2, lo 등)       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ bytes (raw Ethernet frame)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              캡처 레이어 (Capture)                           │
│  ┌─────────────────┐     ┌─────────────────┐                               │
│  │  PacketSniffer  │────▶│   PacketQueue   │                               │
│  │   (sniffer.py)  │     │   (queue.py)    │                               │
│  └─────────────────┘     └─────────────────┘                               │
│         │                        │                                          │
│         │ Scapy sniff()          │ deque[Tuple[datetime, bytes]]            │
│         │ + BPF 필터              │                                          │
│         ▼                        ▼                                          │
│   "udp port 50000"          maxlen=1000                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Tuple[datetime, bytes]
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         처리 레이어 (Processing) ★ NEW                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        PacketProcessor                              │    │
│  │                    (packet_processor.py)                            │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │  1. queue.get_all() → List[Tuple[datetime, bytes]]          │   │    │
│  │  │  2. 언패킹: capture_time, packet_bytes = tuple              │   │    │
│  │  │  3. parser.parse(packet_bytes) → ParseResult                │   │    │
│  │  │  4. store.add(PacketRecord) → 저장                          │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ PacketRecord
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         저장 레이어 (Storage) ★ NEW                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                          PacketStore                                │    │
│  │                       (packet_store.py)                             │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │  _records: deque[PacketRecord]  ← 단일 저장소 (최대 1시간분)  │   │    │
│  │  │                                                              │   │    │
│  │  │  PacketRecord:                                               │   │    │
│  │  │  - timestamp, msg_code, sequence, size                       │   │    │
│  │  │  - jitter_ms, interval_ms                                    │   │    │
│  │  │  - parse_ok, checksum_ok                                     │   │    │
│  │  │  - operation_mode, authority                                 │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  │                              │                                      │    │
│  │                              │ 필요시 변환                           │    │
│  │              ┌───────────────┼───────────────┐                      │    │
│  │              ▼               ▼               ▼                      │    │
│  │      get_stats_dict()  get_logs()    get_chart_data()              │    │
│  │         (통계)          (로그 UI)       (차트 UI)                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Dict (통계 + UI 데이터)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         제공 레이어 (Provider)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        LiveDataProvider                             │    │
│  │                       (live_provider.py)                            │    │
│  │                                                                     │    │
│  │  책임:                                                               │    │
│  │  ├── 캡처 제어 (start/stop/toggle)                                  │    │
│  │  └── _build_state() → DashboardData (Dict, 25키)                   │    │
│  │                                                                     │    │
│  │  출력:                                                               │    │
│  │  {                                                                  │    │
│  │    "connected": True, "interface": "eno2",                         │    │
│  │    "capturePps": 100, "jitterP95": 2.5, "availability": 99.8,     │    │
│  │    "combinedData": [...], "devices": [...], ...                    │    │
│  │  }                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ DashboardData (Dict, 25키)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         프레젠테이션 레이어 (UI)                              │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │   dcc.Store     │────▶│    Callbacks    │────▶│   Components    │       │
│  │ (dashboard-data)│     │(update_callbacks)│    │(panels, charts) │       │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘       │
│         │                        │                        │                 │
│         │ JSON 직렬화             │ Input/Output           │ HTML 렌더링     │
│         ▼                        ▼                        ▼                 │
│   브라우저 메모리           자동 트리거              화면 표시               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 각 파일별 상세 설명

### 2.1. 캡처 레이어

#### 📁 `capture/sniffer.py` - PacketSniffer

| 항목 | 설명 |
|------|------|
| **역할** | 네트워크 인터페이스에서 UDP 패킷 캡처 |
| **입력** | 네트워크 인터페이스 (eno2, lo 등) |
| **출력** | `Tuple[datetime, bytes]` → 콜백 함수로 전달 |

```python
# 출력 예시
self._callback((datetime.now(), bytes(packet[Raw].load)))
```

---

#### 📁 `capture/queue.py` - PacketQueue

| 항목 | 설명 |
|------|------|
| **역할** | 캡처 스레드 ↔ 메인 스레드 간 데이터 전달 |
| **저장** | `deque[Tuple[datetime, bytes]]` (maxlen=1000) |
| **특징** | thread-safe |

---

#### 📁 `capture/packet_processor.py` - PacketProcessor ★ NEW

| 항목 | 설명 |
|------|------|
| **역할** | 패킷 처리 파이프라인 (언패킹, 파싱, 저장) |
| **입력** | `Tuple[datetime, bytes]` from queue |
| **출력** | `ProcessedResult` (처리 요약) |

```python
# 처리 흐름
def process_pending(self) -> ProcessedResult:
    for capture_time, packet_bytes in self._queue.get_all():
        parse_result = self._parser.parse(packet_bytes)
        record = PacketRecord(...)
        self._store.add(record)
    return ProcessedResult(count=..., success_count=..., ...)
```

---

### 2.2. 파싱 레이어

#### 📁 `parser/icd_parser.py` - ICDParser

| 항목 | 설명 |
|------|------|
| **역할** | ICD v1.0 프로토콜 바이너리 파싱 |
| **입력** | `bytes` (raw UDP payload) |
| **출력** | `ParseResult` (header + payload + 상태) |

```python
ParseResult(
    header=ICDHeader(timestamp=1, msg_code=0x01, sequence=1, ...),
    payload=OperationalPayload(operation_mode="무인주행", ...),
    success=True,
    checksum_ok=True
)
```

---

### 2.3. 저장 레이어 ★ NEW

#### 📁 `data/packet_store.py` - PacketStore

| 항목 | 설명 |
|------|------|
| **역할** | 통합 데이터 저장 + 통계/UI 데이터 제공 |
| **저장** | `deque[PacketRecord]` (단일 저장소, 최대 1시간분) |
| **제공** | 통계, 로그, 차트, 이력 데이터 |

```python
@dataclass
class PacketRecord:
    timestamp: datetime
    msg_code: int
    sequence: int
    size: int
    jitter_ms: Optional[float]
    interval_ms: Optional[float]
    parse_ok: bool
    checksum_ok: bool
    operation_mode: str
    authority: str

class PacketStore:
    _records: deque[PacketRecord]
    
    # 통계 제공
    def get_pps(self) -> int
    def get_jitter_percentiles(self) -> Tuple[float, float]
    def get_stats_dict(self) -> Dict
    
    # UI 데이터 제공
    def get_logs(limit: int) -> List[Dict]
    def get_chart_data(limit: int) -> List[Dict]
    def get_connection_history() -> List[Dict]
```

---

### 2.4. 제공 레이어

#### 📁 `data/live_provider.py` - LiveDataProvider

| 항목 | 설명 |
|------|------|
| **역할** | 캡처 제어 + DashboardData 생성 |
| **입력** | PacketStore 데이터 |
| **출력** | `DashboardData` (Dict, 25키) |

```python
# 출력 (DashboardData, 25키)
{
    # 연결 상태 (5키)
    "connected": True,
    "interface": "eno2",
    "direction": "status",
    "filter": "50000→61000",
    "lastPacketTime": "14:30:01",
    
    # 통계 (9키)
    "capturePps": 100,
    "availability": 99.8,
    "jitterCurrent": 1.2,
    "jitterP95": 2.5,
    "jitterP99": 3.8,
    ...
    
    # 운용 상태 (4키)
    "operationalMode": "무인주행",
    "emergencyStatus": {...},
    ...
    
    # UI 데이터 (7키)
    "combinedData": [...],
    "devices": [...],
    "connectionHistory": [...],
    ...
}
```

---

## 3. 데이터 타입 변환 흐름

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 단계         │ 데이터 타입              │ 저장 위치                       │
├──────────────────────────────────────────────────────────────────────────┤
│ 네트워크     │ Ethernet Frame          │ -                              │
│      ↓       │                         │                                │
│ Scapy        │ Packet 객체             │ -                              │
│      ↓       │                         │                                │
│ 캡처         │ Tuple[datetime, bytes]  │ queue (deque)                  │
│      ↓       │                         │                                │
│ 파싱         │ ParseResult             │ - (임시)                       │
│      ↓       │                         │                                │
│ 저장         │ PacketRecord            │ PacketStore (deque) ★          │
│      ↓       │                         │                                │
│ 제공         │ DashboardData (Dict)    │ dcc.Store (JSON)               │
│      ↓       │                         │                                │
│ UI           │ HTML Components         │ 브라우저 DOM                    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 저장되는 데이터 vs 버려지는 데이터

### ✅ 저장되는 데이터

| 위치 | 데이터 | 형태 | 보관 기간 |
|------|--------|------|----------|
| `PacketStore._records` | 모든 패킷 정보 | `deque[PacketRecord]` | 1시간 |
| `dcc.Store` | 대시보드 스냅샷 | JSON | 브라우저 세션 |

### ❌ 버려지는 데이터

| 단계 | 버려지는 것 | 이유 |
|------|------------|------|
| 파싱 후 | raw bytes (원본 패킷) | 메모리 절약, 재사용 불필요 |
| 윈도우 초과 | 오래된 PacketRecord | 분석 범위 외 |

---

## 5. 아키텍처 개선 요약 (2026-02-04)

### Before
```
stats_calculator.py: List[Dict]       → 통계용
live_provider.py:    deque × 5개      → UI용
                     (중복 저장!)
```

### After
```
packet_store.py:     deque[PacketRecord]  → 단일 소스
                     (모든 용도)
```

### 장점
- 중복 제거
- 책임 분리 명확
- 유지보수 용이
- 타입 안전성 (dataclass)

---

## 6. 면접 대비 핵심 포인트

### Q: "왜 단일 저장소로 변경했나요?"

> A: "기존에는 stats_calculator와 live_provider에 같은 데이터가 중복 저장되어 있었습니다. PacketStore로 통합하여 단일 소스를 유지하고, 필요한 형태로 변환해서 제공합니다. 변환 오버헤드(0.5ms)는 2초 갱신 주기에 비해 무시할 수 있습니다."

### Q: "PacketProcessor의 역할은?"

> A: "책임 분리를 위해 도입했습니다. queue 접근, 튜플 언패킹, 파싱, 저장까지의 파이프라인을 담당합니다. live_provider는 캡처 제어와 Dict 생성만 담당합니다."

### Q: "dcc.Store에 PacketRecord를 저장할 수 없나요?"

> A: "아니요. dcc.Store는 JSON 직렬화만 지원하므로, dataclass나 NamedTuple은 직접 저장할 수 없습니다. 그래서 live_provider에서 Dict로 변환해서 저장합니다."
