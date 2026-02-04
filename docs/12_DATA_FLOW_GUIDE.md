# UGV-MON 데이터 흐름 상세 가이드

> 최종 수정: 2026-02-05  
> 목적: 시스템 전체 데이터 흐름 및 각 모듈의 역할 이해

---

## 1. 전체 데이터 흐름 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              네트워크 레이어                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  UGV (무인차량) ──UDP 패킷──▶ 네트워크 인터페이스 (en0, eth0 등)      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ bytes (raw Ethernet frame)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              캡처 레이어 (Capture)                           │
│  ┌─────────────────┐     ┌─────────────────┐                               │
│  │  PacketSniffer  │────▶│   PacketQueue   │                               │
│  │   (sniffer.py)  │     │ (packet_queue.py)│                              │
│  └─────────────────┘     └─────────────────┘                               │
│         │                        │                                          │
│         │ Scapy sniff()          │ (timestamp, bytes) 튜플                  │
│         │ + BPF 필터              │                                          │
│         ▼                        ▼                                          │
│   "udp port 5000"          Queue (thread-safe)                              │
│   Raw 패킷 캡처              잠시 대기 후 전달                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ (datetime, bytes)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              파싱 레이어 (Parsing)                           │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │    ICDParser    │────▶│    ICDHeader    │     │  StatusPayload  │       │
│  │  (icd_parser.py)│     │   (models.py)   │     │   (models.py)   │       │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘       │
│         │                                                                   │
│         │ struct.unpack()                                                   │
│         │ 바이너리 → Python 객체                                             │
│         ▼                                                                   │
│   ParseResult(header, payload, success, checksum_ok, error)                 │
│                                                                             │
│   ※ 여기서 raw bytes는 버려짐! 필요한 정보만 추출                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ ParseResult
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              분석 레이어 (Analysis)                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        StatsCalculator                               │    │
│  │                      (stats_calculator.py)                           │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │  _records: List[Dict]  ← 하이브리드 저장소                    │    │    │
│  │  │  {timestamp, msg_code, sequence, size, jitter_ms, interval_ms}│    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              │ 필요시 변환                            │    │
│  │                              ▼                                       │    │
│  │                       pd.DataFrame                                   │    │
│  │                    (분석 메서드 호출 시)                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ 통계 결과 (Dict)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         데이터 제공 레이어 (Provider)                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        LiveDataProvider                              │    │
│  │                       (live_provider.py)                             │    │
│  │                                                                      │    │
│  │  저장소들 (모두 deque):                                               │    │
│  │  ├── _logs: deque[LogEntry]           ← 로그 100개                   │    │
│  │  ├── _chart_data: deque[Dict]         ← 차트 360개                   │    │
│  │  ├── _availability_history: deque     ← 가용성 3600개                │    │
│  │  ├── _connection_history: deque       ← 연결이력 100개               │    │
│  │  ├── _mode_transitions: deque         ← 모드전이 50개                │    │
│  │  └── _emergency_counts: Dict          ← 비상정지 통계                │    │
│  │                                                                      │    │
│  │  get_current_data() → Dict (JSON 직렬화 가능)                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Dict (JSON 형태)
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
| **입력** | 네트워크 인터페이스 (en0, eth0 등) |
| **출력** | `(datetime, bytes)` 튜플 → 콜백 함수로 전달 |
| **핵심 라이브러리** | Scapy |

```python
# 입력: 네트워크 패킷 (Scapy Packet 객체)
# packet[IP], packet[UDP], packet[Raw] 등으로 접근

# 출력: (캡처 시간, raw 바이트)
self._callback((datetime.now(), bytes(packet[Raw].load)))
```

**주요 메서드:**
- `start()`: 캡처 스레드 시작
- `stop()`: 캡처 중지
- `_process_packet()`: 패킷 처리 및 콜백 호출

---

#### 📁 `capture/packet_queue.py` - PacketQueue

| 항목 | 설명 |
|------|------|
| **역할** | 캡처 스레드 ↔ 메인 스레드 간 데이터 전달 |
| **입력** | `(datetime, bytes)` 튜플 |
| **출력** | 동일한 튜플 (get 시) |
| **특징** | thread-safe, maxsize 제한 |

```python
# 캡처 스레드에서
queue.put((timestamp, raw_data))

# 메인 스레드에서
timestamp, raw_data = queue.get()
```

---

### 2.2. 파싱 레이어

#### 📁 `parsing/icd_parser.py` - ICDParser

| 항목 | 설명 |
|------|------|
| **역할** | ICD v1.0 프로토콜 바이너리 파싱 |
| **입력** | `bytes` (raw UDP payload) |
| **출력** | `ParseResult` (header + payload + 상태) |
| **핵심** | `struct.unpack()` 사용 |

```python
# 입력 예시 (10바이트 헤더 + 페이로드)
raw_data = b'\x00\x00\x00\x01\x00\x01\x00\x00\x00\x14...'

# 출력
ParseResult(
    header=ICDHeader(timestamp=1, msg_code=0x01, sequence=1, data_len=20),
    payload=StatusPayload(operation_mode="자율주행", ...),
    success=True,
    checksum_ok=True,
    error=None
)
```

**파싱 순서:**
1. 헤더 파싱 (10바이트) → `ICDHeader`
2. 체크섬 검증 (마지막 2바이트)
3. 페이로드 파싱 → `StatusPayload`

---

#### 📁 `parsing/models.py` - 데이터 모델

| 클래스 | 필드 |
|--------|------|
| `ICDHeader` | timestamp, msg_code, reserved, data_len, sequence |
| `StatusPayload` | operation_mode, authority, driving_state, devices, emergency |
| `EmergencyStatus` | 각종 비상정지 플래그들 |
| `ParseResult` | header, payload, success, checksum_ok, error |

---

### 2.3. 분석 레이어

#### 📁 `analysis/stats_calculator.py` - StatsCalculator

| 항목 | 설명 |
|------|------|
| **역할** | 실시간 KPI 계산 (PPS, 지터, 가용성 등) |
| **입력** | `(timestamp, sequence, size, msg_code)` |
| **저장** | `List[Dict]` (하이브리드) |
| **분석** | `pd.DataFrame` (필요시 변환) |

```python
# 입력
calc.record_packet(
    timestamp=datetime.now(),
    sequence=5,
    size=100,
    msg_code=0x01
)

# 내부 저장 (_records)
{
    "timestamp": datetime(2026, 2, 5, 6, 30, 0),
    "msg_code": 1,
    "sequence": 5,
    "size": 100,
    "jitter_ms": 2.5,
    "interval_ms": 10.2
}

# 출력 (get_stats_dict)
{
    "pps": 100,
    "jitter_current": 2.5,
    "jitter_p95": 5.0,
    "jitter_p99": 8.0,
    "packet_loss": 3,
    "availability": 98.5
}
```

**왜 하이브리드?**
- `List[Dict]`: 실시간 append 빠름 (O(1))
- `pd.DataFrame`: 분석 시 변환 (quantile, resample 등)

---

### 2.4. 데이터 제공 레이어

#### 📁 `data/live_provider.py` - LiveDataProvider

| 항목 | 설명 |
|------|------|
| **역할** | 모든 데이터 통합 및 UI용 Dict 생성 |
| **입력** | StatsCalculator 통계 + 자체 deque 저장소 |
| **출력** | `Dict` (JSON 직렬화 가능) |

```python
# 내부 저장소 (모두 deque)
_logs              # LogEntry 객체들 (maxlen=100)
_chart_data        # {"timestamp": "12:00:00", "pps": 100, "jitter": 2.5}
_availability_history  # {"timestamp": datetime, "is_up": True}
_connection_history    # {"timestamp": "2026-02-05T06:30:00", "connected": True}
_mode_transitions      # {"from": "수동", "to": "자율", "timestamp": "..."}
_emergency_counts      # {"원격 비상정지": 3, "장애물 감지": 1}

# 출력 (get_current_data)
{
    # 연결 상태
    "isConnected": True,
    "lastPacketTime": "06:30:15",
    
    # 통계 (StatsCalculator에서)
    "capturePps": 100,
    "jitterCurrent": 2.5,
    "availability": 98.5,
    "availabilityHourly": 99.2,
    
    # UI 렌더링용 (deque에서)
    "combinedData": [...],           # 차트 데이터
    "devices": [...],                # 장치 상태
    "availabilitySegments": [...],   # 타임라인
    "msgCodeStats": {...},           # msg_code별 통계
    "connectionHistory": [...],       # 연결 이력
    "modeTransitions": [...],         # 모드 전이
    "emergencyCounts": {...},         # 비상정지 통계
    
    # 운용 상태 (마지막 페이로드에서)
    "operationalMode": "자율주행",
    "operationalAuthority": "원격통제소",
    "emergencyStatus": {...}
}
```

---

### 2.5. 프레젠테이션 레이어

#### 📁 `callbacks/update_callbacks.py` - Dash 콜백

| 항목 | 설명 |
|------|------|
| **역할** | dcc.Store 업데이트 + UI 컴포넌트 업데이트 |
| **입력** | `dcc.Interval` 트리거 (2초마다) |
| **출력** | UI 컴포넌트 props 변경 |

```python
# 데이터 업데이트 콜백
@callback(
    Output("dashboard-data", "data"),
    Input("interval-component", "n_intervals"),
)
def update_data(n):
    return provider.get_current_data()  # Dict → JSON 자동 직렬화

# 컴포넌트 업데이트 콜백
@callback(
    Output("kpi-cards", "children"),
    Input("dashboard-data", "data"),
)
def update_kpi(data):
    return create_kpi_cards_row(data)  # Dash 컴포넌트 반환
```

---

## 3. 데이터 타입 변환 흐름

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 단계         │ 데이터 타입              │ 크기 (예시)                    │
├──────────────────────────────────────────────────────────────────────────┤
│ 네트워크     │ Ethernet Frame          │ ~100 bytes                    │
│      ↓       │                         │                               │
│ Scapy        │ Packet 객체             │ 메모리 상 객체                 │
│      ↓       │                         │                               │
│ 콜백 전달    │ (datetime, bytes)       │ ~110 bytes                    │
│      ↓       │                         │                               │
│ 파싱 후      │ ParseResult             │ Python 객체 ~500 bytes        │
│      ↓       │                         │                               │
│ 통계 저장    │ Dict                    │ ~200 bytes per record         │
│      ↓       │                         │                               │
│ 분석 시      │ pd.DataFrame            │ 전체 데이터 메모리 로드        │
│      ↓       │                         │                               │
│ UI 전달      │ Dict (JSON 호환)        │ ~5KB (전체 상태)              │
│      ↓       │                         │                               │
│ dcc.Store    │ JSON 문자열             │ ~5KB                          │
│      ↓       │                         │                               │
│ 브라우저     │ JavaScript 객체         │ 메모리 상                      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 저장되는 데이터 vs 버려지는 데이터

### ✅ 저장되는 데이터

| 위치 | 데이터 | 형태 | 보관 기간 |
|------|--------|------|----------|
| `StatsCalculator._records` | 패킷 통계 | List[Dict] | 1시간 (window) |
| `_logs` | 로그 | deque | 최근 100개 |
| `_chart_data` | 차트 | deque | 최근 360개 |
| `_availability_history` | 가용성 | deque | 최근 3600개 |
| `_connection_history` | 연결이력 | deque | 최근 100개 |
| `_mode_transitions` | 모드전이 | deque | 최근 50개 |
| `_emergency_counts` | 비상통계 | Dict | 누적 |

### ❌ 버려지는 데이터

| 단계 | 버려지는 것 | 이유 |
|------|------------|------|
| 파싱 후 | raw bytes (원본 패킷) | 메모리 절약, 재사용 불필요 |
| 윈도우 초과 | 오래된 통계 레코드 | 분석 범위 외 |
| maxlen 초과 | 오래된 로그/차트 데이터 | 고정 크기 유지 |

---

## 5. 면접 대비 핵심 포인트

### Q: "왜 raw 데이터를 저장 안 하나요?"

> A: "메모리 효율을 위해서입니다. 100 PPS × 100 bytes × 1시간 = 36MB인데, 실시간 모니터링에서는 과거 raw 데이터가 필요 없고, 파싱된 통계만 있으면 됩니다."

### Q: "왜 deque와 List를 혼용하나요?"

> A: "용도가 다릅니다. deque는 고정 크기 슬라이딩 윈도우에 적합하고 (maxlen 자동 관리), List는 pandas 변환이 필요한 분석용 데이터에 사용합니다."

### Q: "dcc.Store에 DataFrame을 저장할 수 있나요?"

> A: "아니요. dcc.Store는 JSON 직렬화만 지원하므로, Dict/List 형태로 변환해서 저장해야 합니다. DataFrame은 서버 메모리에만 존재합니다."
