# UGV-MON 데이터 흐름 (쉬운 설명)

> 네트워크 패킷이 화면에 표시되기까지의 여정
> **최종 업데이트**: 2026-02-04

---

## 🎯 한 줄 요약

```
UDP → Tuple → PacketProcessor → PacketStore(deque 1개) → Dict(25키) → UI
```

---

## 📊 아키텍처 개선 (2026-02-04)

### Before (복잡, 중복 저장)
```
live_provider.py에서 6가지 책임:
- queue 접근, 언패킹, 파싱, 통계, deque 저장(5개), Dict 생성

저장소: stats_calculator(List) + live_provider(deque 5개) = 중복!
```

### After (단순, 단일 저장)
```
책임 분리:
- packet_processor.py: 패킷 처리 파이프라인
- packet_store.py: 통합 저장소 (deque 1개)
- live_provider.py: 캡처 제어 + Dict 생성

저장소: PacketStore(deque 1개) = 단일 소스!
```

---

## 🗃️ 핵심 자료구조

### 1. PacketRecord (dataclass)
**위치**: `data/packet_store.py`

```python
@dataclass
class PacketRecord:
    timestamp: datetime       # 캡처 시각
    msg_code: int            # ICD 메시지 코드
    sequence: int            # 시퀀스 번호
    size: int                # 패킷 크기
    jitter_ms: Optional[float]
    interval_ms: Optional[float]
    parse_ok: bool           # 파싱 성공 여부
    checksum_ok: bool        # 체크섬 검증
    operation_mode: str      # 운용 모드
    authority: str           # 운용 권한
```

### 2. PacketStore (통합 저장소)
**위치**: `data/packet_store.py`

```python
class PacketStore:
    _records: deque[PacketRecord]  # 단일 저장소 (최대 1시간분)
    
    # 통계 제공
    def get_pps() -> int
    def get_jitter_percentiles() -> Tuple[float, float]
    def get_stats_dict() -> Dict
    
    # UI 데이터 제공
    def get_logs(limit) -> List[Dict]
    def get_chart_data(limit) -> List[Dict]
    def get_connection_history() -> List[Dict]
```

### 3. DashboardData (TypedDict)
**위치**: `data/types.py`

```python
class DashboardData(TypedDict):
    # 연결 (5개)
    connected: bool
    interface: str
    direction: str
    filter: str
    lastPacketTime: str
    
    # 통계 (9개)
    capturePps: int
    availability: float
    jitterCurrent: float
    jitterP95: float
    jitterP99: float
    ...
    
    # 운용 (4개)
    operationalMode: str
    emergencyStatus: Dict
    ...
    
    # UI (7개)
    combinedData: List[Dict]
    devices: List[Dict]
    ...
```

---

## 📦 전체 흐름도 (4단계)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           네트워크 (이더넷)                              │
│                    UDP 패킷: 50000 → 61000 포트                         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. capture/sniffer.py + queue.py                                       │
│     ┌─────────────────────────────────────────────────────────────────┐ │
│     │ 입력: UDP 패킷 (이더넷 프레임)                                    │ │
│     │ 저장: deque[Tuple[datetime, bytes]] (maxlen=1000)               │ │
│     │ 출력: List[Tuple[datetime, bytes]]                              │ │
│     └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. capture/packet_processor.py (NEW)                                   │
│     패킷 처리 파이프라인                                                 │
│     ┌─────────────────────────────────────────────────────────────────┐ │
│     │ 입력: Tuple[datetime, bytes] from queue                        │ │
│     │ 처리:                                                          │ │
│     │   1. Tuple 언패킹 → capture_time, packet_bytes                 │ │
│     │   2. icd_parser.parse(packet_bytes) → ParseResult              │ │
│     │   3. packet_store.add(PacketRecord) → 저장                     │ │
│     │ 출력: ProcessedResult (처리 요약)                               │ │
│     └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. data/packet_store.py (NEW) - 통합 저장소                            │
│     ┌─────────────────────────────────────────────────────────────────┐ │
│     │ 저장: deque[PacketRecord] (단일 저장소, 최대 1시간분)            │ │
│     │                                                                 │ │
│     │ 제공:                                                           │ │
│     │   • get_stats_dict()     → 통계 (PPS, 지터, 손실률)             │ │
│     │   • get_logs()           → 로그 UI용                           │ │
│     │   • get_chart_data()     → 차트 UI용                           │ │
│     │   • get_connection_history() → 이력 UI용                       │ │
│     └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. data/live_provider.py + callbacks/update_callbacks.py               │
│     ┌─────────────────────────────────────────────────────────────────┐ │
│     │ live_provider:                                                  │ │
│     │   • 캡처 제어 (start/stop)                                      │ │
│     │   • PacketStore에서 데이터 가져와 Dict(25키) 생성               │ │
│     │                                                                 │ │
│     │ callbacks:                                                      │ │
│     │   • Dict → HTML/DMC 컴포넌트 변환                               │ │
│     │   • 2초마다 UI 업데이트                                         │ │
│     └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 데이터 타입 변환 요약

| 단계 | 파일 | 입력 타입 | 출력 타입 |
|------|------|----------|----------|
| 1 | sniffer.py | UDP 패킷 | `Tuple[datetime, bytes]` |
| 1 | queue.py | Tuple | `deque` → `List[Tuple]` |
| 2 | packet_processor.py | Tuple | `ProcessedResult` |
| 2-내부 | icd_parser.py | bytes | `ParseResult` |
| 3 | packet_store.py | PacketRecord | `deque` → 통계/UI Dict |
| 4 | live_provider.py | PacketStore | `DashboardData (25키)` |
| 4 | callbacks.py | Dict | HTML 컴포넌트 |

---

## 📂 관련 파일 위치

```
ugv_mon/
├── capture/
│   ├── sniffer.py           # ① UDP 캡처
│   ├── queue.py             # ① 패킷 버퍼 (deque)
│   ├── packet_processor.py  # ② 처리 파이프라인 (NEW)
│   └── stats.py             # 캡처 레벨 카운터
│
├── parser/
│   ├── icd_parser.py        # ② bytes → ParseResult
│   └── models.py            # ICDHeader, OperationalPayload
│
├── data/
│   ├── packet_store.py      # ③ 통합 저장소 (NEW)
│   ├── types.py             # ③ TypedDict 정의 (NEW)
│   ├── live_provider.py     # ④ DashboardData 생성
│   └── mock_data.py         # 테스트용 Mock
│
├── analysis/
│   └── stats_calculator.py  # (하위호환용, PacketStore가 대체)
│
├── callbacks/
│   └── update_callbacks.py  # ④ Dict → UI
│
└── layouts/, components/    # UI 컴포넌트들
```

---

## 🔧 주요 개선 사항

| 항목 | Before | After |
|------|--------|-------|
| **저장소** | stats_calc(List) + live_provider(deque 5개) | PacketStore(deque 1개) |
| **책임** | live_provider 6가지 | 3개 모듈로 분리 |
| **중복** | 같은 데이터 2곳 저장 | 단일 소스 |
| **패킷 레코드** | Dict | dataclass (타입 안전) |
| **대시보드 키** | 26개 (중복) | 25개 |

---

## ⏱️ 실행 주기

| 동작 | 주기 | 설명 |
|------|------|------|
| 패킷 캡처 | 실시간 | scapy가 즉시 수신 |
| 큐 처리 | 2초 | 폴링 인터벌 |
| UI 업데이트 | 2초 | Dash 콜백 |

---

*요약: UDP → Tuple → PacketProcessor → PacketStore → Dict → UI*
