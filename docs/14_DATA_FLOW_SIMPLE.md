# UGV-MON 데이터 흐름 (쉬운 설명)

> 네트워크 패킷이 화면에 표시되기까지의 여정

---

## 🎯 한 줄 요약

```
이더넷 → bytes → deque → ParseResult → PacketRecord → DashboardData → UI
```

---

## 📊 개선된 데이터 타입

### Before (복잡)
```
bytes → Dict → DataFrame(미사용) → Dict(26키, 중복) → UI
```

### After (단순)
```
bytes → ParseResult(dataclass) → PacketRecord(NamedTuple) → DashboardData(25키) → UI
```

---

## 🗃️ 핵심 자료구조

### 1. deque (collections.deque)
**용도**: 실시간 데이터 버퍼 (FIFO, 크기 제한)

| 위치 | 용도 | maxlen |
|------|------|--------|
| `queue.py` | 패킷 임시 저장 | 1000 |
| `live_provider.py` | 로그 저장 | 1000 |
| `live_provider.py` | 차트 데이터 | 180 |
| `live_provider.py` | 연결 이력 | 100 |
| `live_provider.py` | 모드 전이 이력 | 50 |

### 2. PacketRecord (NamedTuple)
**용도**: 통계 계산용 패킷 기록

```python
# stats_calculator.py
class PacketRecord(NamedTuple):
    timestamp: datetime
    msg_code: int
    sequence: int
    size: int
    jitter_ms: Optional[float]
    interval_ms: Optional[float]
```

**왜 NamedTuple?**
- Dict 대비 메모리 50% 감소
- 타입 안전성 보장
- 불변성으로 스레드 안전

### 3. DashboardData (TypedDict)
**용도**: UI에 전달되는 최종 데이터 구조

```python
# data/types.py
class DashboardData(TypedDict):
    # 연결 (5개)
    connected: bool
    interface: str
    direction: str
    filter: str
    lastPacketTime: str
    
    # 통계 (9개)
    capturePps: int
    parseSuccess: float
    availability: float      # 5분 가용성
    availabilityHourly: float # 1시간 가용성
    jitterCurrent: float
    jitterP95: float
    jitterP99: float
    ...
    
    # 운용 (4개)
    operationalMode: str
    emergencyStatus: Dict
    ...
    
    # UI (7개)
    combinedData: List[ChartDataPoint]
    devices: List[DeviceStatus]
    ...
```

---

## 📦 전체 흐름도 (5단계)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           네트워크 (이더넷)                              │
│                    UDP 패킷: 50000 → 61000 포트                         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. sniffer.py + queue.py                                               │
│     ┌─────────────────────────────────────────────────────────────────┐ │
│     │ 입력: UDP 패킷 (이더넷 프레임)                                    │ │
│     │ 저장: ★ deque[Tuple[datetime, bytes]] (maxlen=1000) ★           │ │
│     │ 출력: List[Tuple[datetime, bytes]]                              │ │
│     └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. icd_parser.py                                                       │
│     바이트를 구조체로 파싱                                                │
│     ┌─────────────────────────────────────────────────────────────────┐ │
│     │ 입력: bytes (101 bytes = 12 헤더 + 87 페이로드 + 2 체크섬)        │ │
│     │ 출력: ParseResult (dataclass)                                   │ │
│     │   ├── header: ICDHeader                                        │ │
│     │   └── payload: OperationalPayload                              │ │
│     └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. stats_calculator.py                                                 │
│     통계 계산 (PPS, 지터, 가용성 등)                                      │
│     ┌─────────────────────────────────────────────────────────────────┐ │
│     │ 입력: timestamp, sequence, size, msg_code                       │ │
│     │ 저장: ★ List[PacketRecord] (NamedTuple, 최대 1시간분) ★          │ │
│     │ 출력: dict (pps, jitter_p95, availability 등)                   │ │
│     └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. live_provider.py                                                    │
│     모든 데이터를 DashboardData (25개 키)로 통합                          │
│     ┌─────────────────────────────────────────────────────────────────┐ │
│     │ 입력: ParseResult + StatsCalculator 결과                        │ │
│     │ 저장: ★ deque 여러 개 (이력 데이터) ★                             │ │
│     │ 출력: DashboardData (TypedDict, 25개 키)                        │ │
│     │   ├── 연결: connected, interface, direction... (5개)           │ │
│     │   ├── 통계: capturePps, jitter, availability... (9개)          │ │
│     │   ├── 운용: operationalMode, emergencyStatus... (4개)          │ │
│     │   └── UI: combinedData, devices, history... (7개)              │ │
│     └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. update_callbacks.py → 브라우저                                       │
│     DashboardData → UI 컴포넌트 → 화면 표시                              │
│     ┌─────────────────────────────────────────────────────────────────┐ │
│     │ 입력: DashboardData (Dict)                                      │ │
│     │ 출력: HTML/DMC 컴포넌트들                                         │ │
│     │   ├── KPI 카드 (PPS, 지터, 가용성)                               │ │
│     │   ├── 차트 (Plotly Figure)                                      │ │
│     │   ├── 상태 패널 (운용모드, 비상정지)                              │ │
│     │   └── 히스토리 패널 (연결이력, 모드전이)                          │ │
│     └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 데이터 타입 변환 요약

| 단계 | 파일 | 입력 타입 | 저장/처리 타입 | 출력 타입 |
|------|------|----------|---------------|----------|
| 1 | sniffer.py | UDP 패킷 | - | `Tuple[datetime, bytes]` |
| 1 | queue.py | 튜플 | **`deque`** | `List[Tuple]` |
| 2 | icd_parser.py | `bytes` | - | **`ParseResult`** |
| 3 | stats_calculator.py | 숫자들 | **`List[PacketRecord]`** | `dict` |
| 4 | live_provider.py | 여러 객체 | **`deque`** 여러개 | **`DashboardData`** |
| 5 | callbacks.py | `Dict` | - | HTML 컴포넌트 |

---

## 📝 핵심 데이터 구조 예시

### 1. 원본 패킷 (bytes)

```
[헤더 12B][페이로드 87B][체크섬 2B] = 총 101 bytes
```

### 2. ParseResult (파싱 후)

```python
ParseResult(
    success=True,
    header=ICDHeader(timestamp=100, sequence=5, msg_code=0x01, ...),
    payload=OperationalPayload(operation_mode="무인주행", devices={...}, ...),
    checksum_ok=True
)
```

### 3. PacketRecord (통계용)

```python
PacketRecord(
    timestamp=datetime(2026, 2, 4, 14, 30, 1),
    msg_code=0x01,
    sequence=5,
    size=101,
    jitter_ms=1.2,
    interval_ms=10.0
)
```

### 4. DashboardData (UI용, 25개 키)

```python
{
    # 연결 상태 (5개)
    "connected": True,
    "interface": "eno2",
    "direction": "status",
    "filter": "50000→61000",
    "lastPacketTime": "14:30:01",
    
    # 통계 (9개)
    "capturePps": 100,
    "availability": 99.8,
    "availabilityHourly": 99.5,
    "jitterCurrent": 1.2,
    "jitterP95": 2.5,
    "jitterP99": 3.8,
    ...
    
    # 운용 상태 (4개)
    "operationalMode": "무인주행",
    "operationalAuthority": "OCS",
    "drivingState": "주행",
    "emergencyStatus": {"통신이상": False, ...},
    
    # UI 데이터 (7개)
    "combinedData": [{"timestamp": "14:30:01", "pps": 100, "jitter": 1.2}, ...],
    "devices": [{"name": "모터", "connected": True}, ...],
    "connectionHistory": [...],
    "modeTransitions": [...],
    "emergencyCounts": {"통신이상": 2},
    ...
}
```

---

## ⏱️ 실행 주기

| 동작 | 주기 | 설명 |
|------|------|------|
| 패킷 캡처 | 실시간 | scapy가 즉시 수신 |
| 큐 처리 | 2초 | 폴링 인터벌 |
| UI 업데이트 | 2초 | Dash 콜백 |

---

## 📂 관련 파일 위치

```
ugv_mon/
├── capture/
│   ├── sniffer.py      # ① 패킷 캡처
│   └── queue.py        # ① 큐 저장 (deque)
├── parser/
│   ├── icd_parser.py   # ② 바이트→ParseResult
│   └── models.py       # ② ICDHeader, OperationalPayload
├── analysis/
│   └── stats_calculator.py  # ③ PacketRecord, 통계 계산
├── data/
│   ├── live_provider.py     # ④ DashboardData 생성
│   └── types.py             # ④ TypedDict 정의
├── callbacks/
│   └── update_callbacks.py  # ⑤ Dict→UI
└── core/
    └── models.py       # 공통 데이터 클래스 정의
```

---

## 🔧 개선 요약 (2026-02-04)

| 항목 | Before | After |
|------|--------|-------|
| 패킷 레코드 | `List[Dict]` | `List[PacketRecord]` (NamedTuple) |
| DataFrame | 있음 (미사용 dead code) | 제거됨 (ML 도입 시 별도 모듈) |
| 대시보드 키 | 26개 (중복 있음) | 25개 (중복 제거) |
| 타입 문서화 | 없음 | `data/types.py` (TypedDict) |

---

*요약: 네트워크 바이트 → ParseResult → PacketRecord → DashboardData → 화면*
