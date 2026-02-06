# UGV-MON 데이터 흐름 가이드

> **최종 수정**: 2026-02-04  
> **목적**: 네트워크 패킷이 화면에 표시되기까지의 전체 흐름 이해

---

## 1. 한 줄 요약

```
UDP → Tuple → PacketProcessor → PacketStore(deque 1개) → Dict(25키) → UI
```

---

## 2. 전체 흐름도

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              네트워크 레이어                                  │
│         UGV (무인차량) ──UDP 패킷──▶ 인터페이스 (eno2, lo)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ bytes
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. 캡처 레이어                                                              │
│     sniffer.py + queue.py                                                   │
│     ─────────────────────────────────────────────────────────────────────   │
│     • Scapy로 UDP 패킷 캡처                                                  │
│     • 저장: deque[Tuple[datetime, bytes]] (maxlen=1000)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Tuple[datetime, bytes]
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. 처리 레이어                                                              │
│     packet_processor.py                                                     │
│     ─────────────────────────────────────────────────────────────────────   │
│     • Tuple 언패킹 → capture_time, packet_bytes                             │
│     • icd_parser.parse() → ParseResult                                      │
│     • packet_store.add() → 저장                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ PacketRecord
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. 저장 레이어                                                              │
│     packet_store.py                                                         │
│     ─────────────────────────────────────────────────────────────────────   │
│     • 저장: deque[PacketRecord] (단일 저장소, 최대 1시간분)                   │
│     • 제공: get_stats_dict(), get_logs(), get_chart_data()                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Dict
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. 제공 + UI 레이어                                                         │
│     live_provider.py + update_callbacks.py                                  │
│     ─────────────────────────────────────────────────────────────────────   │
│     • 캡처 제어 (start/stop)                                                │
│     • DashboardData (Dict, 25키) 생성                                       │
│     • Dict → HTML/DMC 컴포넌트 변환 (2초마다)                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 핵심 데이터 구조

### 3.1 PacketRecord (통합 레코드)

```python
# data/packet_store.py
@dataclass
class PacketRecord:
    timestamp: datetime       # 캡처 시각
    msg_code: int            # ICD 메시지 코드 (0x01, 0x10 등)
    sequence: int            # 시퀀스 번호 (0~15)
    size: int                # 패킷 크기 (bytes)
    jitter_ms: Optional[float]
    interval_ms: Optional[float]
    parse_ok: bool           # 파싱 성공 여부
    checksum_ok: bool        # 체크섬 검증
    operation_mode: str      # 운용 모드
    authority: str           # 운용 권한
```

### 3.2 PacketStore (통합 저장소)

```python
# data/packet_store.py
class PacketStore:
    _records: deque[PacketRecord]  # 단일 저장소
    
    # 통계 제공
    def get_pps() -> int
    def get_jitter_percentiles() -> Tuple[float, float]
    def get_stats_dict() -> Dict
    
    # UI 데이터 제공 (필요시 Dict로 변환)
    def get_logs(limit) -> List[Dict]
    def get_chart_data(limit) -> List[Dict]
    def get_connection_history() -> List[Dict]
```

### 3.3 DashboardData (UI 전달용)

```python
# data/types.py
DashboardData = {
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
    ...
    
    # 운용 상태 (4키)
    "operationalMode": "무인주행",
    "emergencyStatus": {...},
    ...
    
    # UI 데이터 (7키)
    "combinedData": [...],
    "devices": [...],
    ...
}
```

---

## 4. 파일별 역할

| 파일 | 역할 | 입력 | 출력 |
|------|------|------|------|
| `sniffer.py` | UDP 캡처 | 네트워크 | `Tuple[datetime, bytes]` |
| `queue.py` | 버퍼 저장 | Tuple | `deque` |
| `packet_processor.py` | 처리 파이프라인 | Tuple | `BatchProcessResult` |
| `icd_parser.py` | 바이트 파싱 | bytes | `ParseResult` |
| `packet_store.py` | 통합 저장 | PacketRecord | 통계/UI Dict |
| `live_provider.py` | 캡처 제어 + Dict 생성 | PacketStore | `DashboardData` |
| `update_callbacks.py` | UI 변환 | Dict | HTML 컴포넌트 |

---

## 5. 데이터 타입 변환 흐름

| 단계 | 위치 | 타입 | 저장? |
|------|------|------|-------|
| 네트워크 | - | Ethernet Frame | ❌ |
| 캡처 | queue.py | `Tuple[datetime, bytes]` | ✅ deque |
| 파싱 | icd_parser.py | `ParseResult` | ❌ 임시 |
| 저장 | packet_store.py | `PacketRecord` | ✅ deque |
| 제공 | live_provider.py | `DashboardData (Dict)` | ✅ dcc.Store |
| UI | callbacks.py | HTML Components | ❌ |

---

## 6. 저장 vs 버림

### ✅ 저장되는 데이터

| 위치 | 형태 | 보관 기간 |
|------|------|----------|
| `queue.py` | `deque[Tuple]` | 처리 전까지 |
| `packet_store.py` | `deque[PacketRecord]` | 1시간 |
| `dcc.Store` | JSON | 브라우저 세션 |

### ❌ 버려지는 데이터

| 데이터 | 이유 |
|--------|------|
| raw bytes (원본 패킷) | 파싱 후 불필요, 메모리 절약 |
| ParseResult | 임시 객체, PacketRecord로 변환 |
| 1시간 초과 레코드 | 분석 범위 외 |

---

## 7. 아키텍처 개선 (2026-02-04)

### Before (복잡)
```
live_provider.py: 6가지 책임
├── queue 접근
├── Tuple 언패킹
├── parser 호출
├── stats_calc 호출 → List[Dict] 저장
├── deque 5개 저장 (로그, 차트, 이력 등)
└── Dict 생성

저장소: 2곳에 중복 저장
```

### After (단순)
```
packet_processor.py: 처리 파이프라인
packet_store.py:     통합 저장소 (deque 1개)
live_provider.py:    캡처 제어 + Dict 생성

저장소: 단일 소스
```

### 개선 효과

| 항목 | Before | After |
|------|--------|-------|
| 저장소 | 2곳 (중복) | 1곳 |
| 책임 | 6가지 혼재 | 3개 모듈 분리 |
| 레코드 타입 | Dict | dataclass |
| 대시보드 키 | 26개 (중복) | 25개 |

---

## 8. 실행 주기

| 동작 | 주기 |
|------|------|
| 패킷 캡처 | 실시간 (scapy) |
| 큐 처리 | 2초 |
| UI 업데이트 | 2초 |

---

## 9. 파일 위치

```
ugv_mon/
├── capture/
│   ├── sniffer.py           # ① UDP 캡처
│   ├── queue.py             # ① 버퍼
│   └── packet_processor.py  # ② 처리 파이프라인
│
├── parser/
│   ├── icd_parser.py        # ② bytes → ParseResult
│   └── models.py            # ICDHeader, OperationalPayload
│
├── data/
│   ├── packet_store.py      # ③ 통합 저장소
│   ├── types.py             # ③ TypedDict 정의
│   └── live_provider.py     # ④ DashboardData 생성
│
└── callbacks/
    └── update_callbacks.py  # ④ Dict → UI
```

---

## 10. 면접 대비 Q&A

### Q: "왜 단일 저장소로 변경했나요?"

> PacketStore가 유일한 데이터 소스입니다. 단일 deque에 모든 PacketRecord를 저장하고, get_stats_dict(), get_logs(), get_chart_data() 등으로 용도에 맞게 변환하여 제공합니다. 변환 오버헤드(0.5ms)는 2초 갱신 주기에 비해 무시할 수 있습니다.

### Q: "PacketProcessor의 역할은?"

> 책임 분리를 위해 도입했습니다. queue 접근, 튜플 언패킹, 파싱, 저장까지의 파이프라인을 담당합니다. live_provider는 캡처 제어와 Dict 생성만 담당합니다.

### Q: "dcc.Store에 PacketRecord를 저장할 수 없나요?"

> 아니요. dcc.Store는 JSON 직렬화만 지원하므로, dataclass나 NamedTuple은 직접 저장할 수 없습니다. 그래서 live_provider에서 Dict로 변환해서 저장합니다.

### Q: "raw bytes를 왜 저장 안 하나요?"

> 메모리 효율을 위해서입니다. 100 PPS × 100 bytes × 1시간 = 36MB인데, 실시간 모니터링에서는 과거 raw 데이터가 필요 없고, 파싱된 통계만 있으면 됩니다.

---

*요약: UDP → Tuple → PacketProcessor → PacketStore → Dict → UI*
