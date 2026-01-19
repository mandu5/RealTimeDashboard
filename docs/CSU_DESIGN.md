# CSU별 설계고려사항 및 Class Diagram

> **작성일**: 2026-01-20  
> **버전**: 1.0  
> **목적**: 각 CSU(Computer Software Unit)의 설계 고려사항 및 클래스 다이어그램 정의

---

## 1. CSU 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│                         UGV-MON (CSCI)                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────┐ │
│   │   CSC-001       │   │    CSC-002       │   │    CSC-003       │ │
│   │ Data Acquisition│──▶│ Data Processing  │──▶│ Data Presentation│ │
│   │   (데이터 획득)  │   │  (데이터 처리)    │   │   (데이터 표현)   │ │
│   └─────────────────┘   └──────────────────┘   └──────────────────┘ │
│          │                      │                       │            │
│   ┌──────┴──────┐       ┌───────┴───────┐       ┌───────┴──────┐    │
│   │CSU-001-001  │       │CSU-002-001    │       │CSU-003-001   │    │
│   │PacketSniffer│       │ICDParser      │       │DashboardUI   │    │
│   │             │       │               │       │              │    │
│   │CSU-001-002  │       │CSU-002-002    │       │CSU-003-002   │    │
│   │PacketQueue  │       │StatsCalculator│       │ChartRenderer │    │
│   └─────────────┘       └───────────────┘       └──────────────┘    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. CSU-001: Data Acquisition (데이터 획득)

### 2.1 CSU-001-001: PacketSniffer

**설계 고려사항**:

| 항목 | 고려사항 | 결정 |
|------|----------|------|
| 라이브러리 | raw socket vs Scapy | Scapy (BPF 필터, 추상화 수준 높음) |
| 스레딩 | 메인 vs 별도 스레드 | 별도 daemon 스레드 (UI 블로킹 방지) |
| 권한 | root 필요 여부 | 필요 (sudo python run.py) |
| 필터링 | 커널 vs 애플리케이션 | BPF 커널 필터 (성능) |
| 에러 처리 | 권한 오류, 인터페이스 없음 | 명확한 에러 메시지 |

**Class Diagram**:

```
┌─────────────────────────────────────────────────────────┐
│                     PacketSniffer                        │
├─────────────────────────────────────────────────────────┤
│ - _interface: str          # 캡처 인터페이스 (lo, eno2) │
│ - _filter: str             # BPF 필터 문자열           │
│ - _callback: Callable      # 패킷 수신 콜백 함수       │
│ - _running: bool           # 실행 상태 플래그          │
│ - _thread: Thread          # 캡처 스레드               │
│ - _stats: CaptureStats     # 캡처 통계                 │
├─────────────────────────────────────────────────────────┤
│ + __init__(interface, src_port, dst_port, callback)     │
│ + start() -> None          # 캡처 시작 (스레드 생성)   │
│ + stop() -> None           # 캡처 중지 (스레드 종료)   │
│ + is_running() -> bool     # 실행 상태 확인            │
│ + get_stats() -> CaptureStats  # 통계 반환            │
│ - _capture_loop() -> None  # 내부 캡처 루프            │
│ - _process_packet(pkt) -> None  # 패킷 처리 콜백      │
└─────────────────────────────────────────────────────────┘
                            │
                            │ uses
                            ▼
┌─────────────────────────────────────────────────────────┐
│                     CaptureStats                         │
├─────────────────────────────────────────────────────────┤
│ + packets_total: int       # 총 캡처 패킷 수           │
│ + packets_filtered: int    # 필터 통과 패킷 수         │
│ + bytes_total: int         # 총 바이트 수              │
│ + start_time: datetime     # 캡처 시작 시간            │
│ + last_packet_time: datetime  # 마지막 패킷 시간       │
├─────────────────────────────────────────────────────────┤
│ + get_pps() -> int         # 초당 패킷 수 계산         │
│ + get_filter_pass_pct() -> float  # 필터 통과율       │
│ + reset() -> None          # 통계 초기화               │
└─────────────────────────────────────────────────────────┘
```

### 2.2 CSU-001-002: PacketQueue

**설계 고려사항**:

| 항목 | 고려사항 | 결정 |
|------|----------|------|
| 자료구조 | list vs deque vs Queue | collections.deque (maxlen) |
| 동기화 | Lock 필요 여부 | threading.Lock (producer-consumer) |
| 버퍼 크기 | 무제한 vs 고정 | 고정 (1000개, 메모리 보호) |
| 오버플로 | 예외 vs 드롭 | 드롭 (oldest, maxlen 동작) |

**Class Diagram**:

```
┌─────────────────────────────────────────────────────────┐
│                     PacketQueue                          │
├─────────────────────────────────────────────────────────┤
│ - _queue: deque[bytes]     # 패킷 바이트 큐            │
│ - _lock: threading.Lock    # 동기화 락                 │
│ - _max_size: int           # 최대 큐 크기              │
├─────────────────────────────────────────────────────────┤
│ + __init__(max_size: int = 1000)                        │
│ + put(packet: bytes) -> None   # 패킷 추가             │
│ + get() -> Optional[bytes]     # 패킷 꺼내기           │
│ + get_all() -> List[bytes]     # 모든 패킷 꺼내기      │
│ + size() -> int                # 현재 큐 크기          │
│ + clear() -> None              # 큐 비우기             │
└─────────────────────────────────────────────────────────┘
```

---

## 3. CSU-002: Data Processing (데이터 처리/분석)

### 3.1 CSU-002-001: ICDParser

**설계 고려사항**:

| 항목 | 고려사항 | 결정 |
|------|----------|------|
| 파싱 방식 | struct vs 수동 | struct.unpack (안전, 명확) |
| 엔디안 | Big vs Little | Little Endian (ICD 규격) |
| 에러 처리 | 예외 vs 결과 객체 | ParseResult 객체 (성공/실패 포함) |
| 체크섬 | 무시 vs 검증 | 검증 (sum & 0xFFFF) |

**Class Diagram**:

```
┌─────────────────────────────────────────────────────────┐
│                       ICDParser                          │
├─────────────────────────────────────────────────────────┤
│ - _header_format: str      # struct 포맷 문자열        │
│ - _config: ICDConfig       # ICD 설정                  │
├─────────────────────────────────────────────────────────┤
│ + parse(data: bytes) -> ParseResult                     │
│ + parse_header(data: bytes) -> Optional[ICDHeader]      │
│ + parse_status_report(data: bytes) -> Optional[StatusReport] │
│ + verify_checksum(data: bytes) -> bool                  │
│ - _extract_operation_mode(byte: int) -> OperationMode   │
│ - _extract_authority(byte: int) -> Authority            │
│ - _extract_driving_state(byte: int) -> DrivingState     │
│ - _extract_device_presence(word: int) -> Dict[str, bool] │
│ - _extract_emergency_status(word: int) -> Dict[str, bool] │
└─────────────────────────────────────────────────────────┘
                            │
                            │ returns
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      ParseResult                         │
├─────────────────────────────────────────────────────────┤
│ + success: bool            # 파싱 성공 여부            │
│ + header: Optional[ICDHeader]   # 파싱된 헤더          │
│ + payload: Optional[StatusReport]  # 파싱된 페이로드   │
│ + checksum_ok: bool        # 체크섬 검증 결과          │
│ + error: str               # 에러 메시지 (실패 시)     │
│ + raw_data: bytes          # 원본 데이터               │
├─────────────────────────────────────────────────────────┤
│ + is_status_report() -> bool   # 상태보고 메시지 여부  │
└─────────────────────────────────────────────────────────┘
                            │
                            │ contains
                            ▼
┌─────────────────────────────────────────────────────────┐
│                       ICDHeader                          │
├─────────────────────────────────────────────────────────┤
│ + timestamp: int           # 타임스탬프 (4바이트)      │
│ + sequence: int            # 시퀀스 번호 (하위 1바이트) │
│ + source_id: int           # 송신 장비 ID             │
│ + dest_id: int             # 수신 장비 ID             │
│ + msg_code: int            # 메시지 코드              │
│ + ack_code: int            # 응답 코드                │
│ + data_length: int         # 데이터 길이              │
└─────────────────────────────────────────────────────────┘
```

### 3.2 CSU-002-002: StatsCalculator

**설계 고려사항**:

| 항목 | 고려사항 | 결정 |
|------|----------|------|
| 지터 계산 | 평균 vs 백분위수 | P95/P99 (이상치 민감) |
| 손실 추정 | 개수 vs 비율 | 개수 (seq gap 기반) |
| 가용성 | 단순 vs 시간 가중 | 시간 가중 (5분/1시간) |
| 버퍼 | 무제한 vs 슬라이딩 윈도우 | 슬라이딩 윈도우 (메모리) |

**Class Diagram**:

```
┌─────────────────────────────────────────────────────────┐
│                    StatsCalculator                       │
├─────────────────────────────────────────────────────────┤
│ - _jitter_buffer: deque[float]  # 지터 값 버퍼         │
│ - _packet_times: deque[datetime]  # 패킷 수신 시간     │
│ - _last_seq: int           # 마지막 시퀀스 번호        │
│ - _loss_count: int         # 손실 패킷 수              │
│ - _up_time: float          # 가동 시간 (초)            │
│ - _total_time: float       # 전체 시간 (초)            │
├─────────────────────────────────────────────────────────┤
│ + add_packet(timestamp: datetime, seq: int) -> None     │
│ + calculate_jitter_p95() -> float                       │
│ + calculate_jitter_p99() -> float                       │
│ + calculate_pps(window_sec: int = 1) -> int             │
│ + get_packet_loss() -> int                              │
│ + calculate_availability(window_sec: int) -> float      │
│ + update_availability(is_connected: bool) -> None       │
│ - _detect_loss(current_seq: int) -> int                 │
│ - _calculate_percentile(values: List, pct: float) -> float │
└─────────────────────────────────────────────────────────┘
```

---

## 4. CSU-003: Data Presentation (데이터 표현)

### 4.1 CSU-003-001: DashboardUI

**설계 고려사항**:

| 항목 | 고려사항 | 결정 |
|------|----------|------|
| 프레임워크 | Flask vs Dash | Dash (Plotly 통합) |
| 컴포넌트 | Dash HTML vs DMC | DMC (기업 UI, 일관성) |
| 상태 관리 | 전역 vs Store | dcc.Store (React 패턴) |
| 갱신 방식 | WebSocket vs Polling | Polling (단순, 안정) |

**Class Diagram**:

```
┌─────────────────────────────────────────────────────────┐
│                       DashboardUI                        │
├─────────────────────────────────────────────────────────┤
│ (Dash 컴포넌트 기반 - 클래스가 아닌 함수형 구조)        │
├─────────────────────────────────────────────────────────┤
│ Layout Functions:                                        │
│ + create_main_layout(data, logs) -> MantineProvider     │
│ + create_header(status_data) -> dmc.Card                │
│ + create_kpi_row(metrics) -> dmc.SimpleGrid             │
│ + create_status_panel(state) -> dmc.Card                │
│ + create_charts_panel(chart_data) -> dmc.Card           │
│ + create_log_panel(logs) -> dmc.Card                    │
│                                                          │
│ Callback Functions:                                      │
│ + register_callbacks(app) -> None                        │
│ + update_dashboard_data(n_intervals, paused, data)      │
│ + update_all_components(data, time_range)               │
│ + toggle_pause(n_clicks) -> bool                         │
│ + clear_logs(n_clicks) -> List                          │
└─────────────────────────────────────────────────────────┘
```

### 4.2 CSU-003-002: ChartRenderer

**설계 고려사항**:

| 항목 | 고려사항 | 결정 |
|------|----------|------|
| 라이브러리 | Matplotlib vs Plotly | Plotly (인터랙티브, Dash 통합) |
| 갱신 방식 | 전체 재렌더 vs 부분 | 전체 재렌더 (Dash 패턴) |
| 시간 범위 | 고정 vs 선택 | 선택 가능 (30s/1m/5m) |
| 상호작용 | 활성화 vs 비활성화 | 비활성화 (모니터링 전용) |

**Class Diagram**:

```
┌─────────────────────────────────────────────────────────┐
│                    ChartRenderer                         │
├─────────────────────────────────────────────────────────┤
│ (함수 기반 구조)                                         │
├─────────────────────────────────────────────────────────┤
│ + create_communication_chart(data, p95, p99, time_range) │
│   -> go.Figure                                           │
│   - PPS 트레이스 (위쪽 서브플롯)                         │
│   - Jitter 트레이스 (아래쪽 서브플롯)                    │
│   - P95/P99 참조선                                       │
│                                                          │
│ + create_availability_timeline(segments) -> go.Figure    │
│   - Up 세그먼트 (초록색)                                 │
│   - Down 세그먼트 (빨간색)                               │
│   - 전체 영역 hover 정보                                 │
│                                                          │
│ + get_chart_colors() -> Dict[str, str]                   │
│   - primary, secondary, success, danger 등               │
└─────────────────────────────────────────────────────────┘
```

---

## 5. 데이터 흐름 시퀀스

```
┌──────────┐    ┌───────────┐    ┌──────────┐    ┌────────────┐    ┌──────────┐
│ Network  │    │PacketSniff│    │ ICDParser│    │StatsCalcul │    │DashboardUI│
│ (VIC→OCS)│    │   er      │    │          │    │    ator    │    │          │
└────┬─────┘    └─────┬─────┘    └────┬─────┘    └─────┬──────┘    └────┬─────┘
     │                │               │                │                │
     │  UDP Packet    │               │                │                │
     │───────────────▶│               │                │                │
     │                │               │                │                │
     │                │  Raw Bytes    │                │                │
     │                │──────────────▶│                │                │
     │                │               │                │                │
     │                │               │  ParseResult   │                │
     │                │               │───────────────▶│                │
     │                │               │                │                │
     │                │               │                │  Stats Update  │
     │                │               │                │───────────────▶│
     │                │               │                │                │
     │                │               │                │                │
     │    ┌───────────────────────────────────────────────────────────┐│
     │    │                    2초 Polling Cycle                       ││
     │    │                                                            ││
     │    │  dcc.Interval ──▶ update_dashboard_data callback          ││
     │    │                          │                                 ││
     │    │                          ▼                                 ││
     │    │              update_all_components callback                ││
     │    │                          │                                 ││
     │    │                          ▼                                 ││
     │    │                    UI 컴포넌트 갱신                         ││
     │    └───────────────────────────────────────────────────────────┘│
     │                                                                  │
```

---

## 6. 파일-CSU 매핑

| CSU | 파일 | 설명 |
|-----|------|------|
| CSU-001-001 | `ugv_mon/capture/sniffer.py` | Scapy 패킷 캡처 |
| CSU-001-002 | `ugv_mon/capture/queue.py` | 패킷 버퍼 큐 |
| CSU-002-001 | `ugv_mon/parser/icd_parser.py` | ICD v1.0 파싱 |
| CSU-002-002 | `ugv_mon/analysis/stats.py` | 통계 분석 |
| CSU-003-001 | `ugv_mon/layouts/*.py` | 대시보드 UI |
| CSU-003-002 | `ugv_mon/layouts/charts.py` | 차트 렌더링 |

---

## 7. 설계 결정 요약

### 7.1 왜 Scapy인가?

1. **BPF 커널 필터**: 애플리케이션 레벨보다 효율적
2. **추상화**: raw socket 대비 간결한 API
3. **크로스 플랫폼**: loopback/물리 인터페이스 모두 지원
4. **디버깅 용이**: 개발 중 패킷 내용 검사 가능

### 7.2 왜 struct 모듈인가?

1. **안전성**: 수동 바이트 슬라이싱보다 명확
2. **엔디안 처리**: `<` (little-endian) 명시적 지정
3. **타입 안전**: 정수 크기 명확 (`H`, `I` 등)
4. **성능**: C 레벨 구현

### 7.3 왜 Polling인가?

1. **단순성**: WebSocket 연결 관리 불필요
2. **안정성**: 연결 끊김 처리 불필요
3. **충분한 실시간성**: 2초 간격으로 모니터링 목적 충족
4. **Dash 친화적**: `dcc.Interval` 내장 컴포넌트

### 7.4 왜 DMC인가?

1. **기업 UI**: 전문적인 외관
2. **일관성**: 모든 컴포넌트가 동일한 디자인 시스템
3. **성능**: 최적화된 React 컴포넌트
4. **문서화**: 상세한 API 문서
