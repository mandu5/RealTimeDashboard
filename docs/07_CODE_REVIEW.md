# UGV-MON 코드 리뷰 보고서

> **리뷰 일자**: 2026-01-27  
> **리뷰어**: AI Code Reviewer  
> **프로젝트 버전**: 1.0.0

---

## 1. 개요

### 1.1 프로젝트 목적
VIC(차량연동통제기)와 OCS(운용통제기) 간 UDP 통신을 **수동 감시**하는 실시간 대시보드.

### 1.2 기술 스택

| 구분 | 기술 | 버전 |
|------|------|------|
| 언어 | Python | 3.x |
| 웹 프레임워크 | Dash | 2.14.2 |
| UI 컴포넌트 | dash-mantine-components | 0.12.1 |
| 테이블 | dash-ag-grid | 31.0.1 |
| 시각화 | Plotly | 5.18.0 |
| 패킷 캡처 | Scapy | 2.5.0 |
| 테스트 | pytest | >=7.0.0 |

### 1.3 프로젝트 규모

| 항목 | 수량 |
|------|------|
| Python 파일 | 27개 |
| 테스트 파일 | 2개 (36개 테스트 케이스) |
| 문서 파일 | 8개 |
| 총 코드 라인 | 약 2,500줄 |

---

## 2. 아키텍처 분석

### 2.1 디렉토리 구조

```
opus1/
├── run.py                    # 통합 CLI 진입점
├── requirements.txt          # 의존성
├── test_capture_packets.py   # 통합 테스트
│
├── tests/                    # 단위 테스트
│   ├── test_icd_parser.py
│   └── test_stats_calculator.py
│
├── docs/                     # 문서 (8개)
│
└── ugv_mon/                  # 메인 패키지
    ├── app.py               # Dash 앱 팩토리
    ├── config.py            # 설정 관리
    ├── constants.py         # 상수 정의
    ├── styles.py            # UI 스타일
    │
    ├── capture/             # 패킷 캡처 계층
    │   ├── sniffer.py       # Scapy 스니퍼
    │   ├── queue.py         # 패킷 큐
    │   └── stats.py         # 캡처 통계
    │
    ├── parser/              # ICD 프로토콜 파싱
    │   ├── icd_parser.py    # 헤더 파서
    │   └── models.py        # 데이터 모델
    │
    ├── analysis/            # 통계 분석
    │   └── stats_calculator.py  # PPS, 지터, 손실
    │
    ├── data/                # 데이터 제공자
    │   ├── live_provider.py # 실시간 데이터
    │   ├── mock_data.py     # 테스트용 Mock
    │   └── models.py        # 대시보드 모델
    │
    ├── components/          # UI 컴포넌트
    │   ├── kpi_card.py
    │   ├── device_grid.py
    │   ├── log_table.py
    │   └── status_chip.py
    │
    ├── layouts/             # 레이아웃
    │   ├── main_layout.py
    │   ├── header.py
    │   ├── panels.py
    │   └── charts.py
    │
    └── callbacks/           # Dash 콜백
        └── update_callbacks.py
```

### 2.2 계층 구조

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│  (layouts/, components/, callbacks/)                         │
├─────────────────────────────────────────────────────────────┤
│                      Data Provider Layer                     │
│  (data/live_provider.py, data/mock_data.py)                 │
├─────────────────────────────────────────────────────────────┤
│                      Analysis Layer                          │
│  (analysis/stats_calculator.py)                             │
├─────────────────────────────────────────────────────────────┤
│                      Parser Layer                            │
│  (parser/icd_parser.py, parser/models.py)                   │
├─────────────────────────────────────────────────────────────┤
│                      Capture Layer                           │
│  (capture/sniffer.py, capture/queue.py)                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 데이터 흐름

```
[Network Packets]
       │
       ▼
┌─────────────────┐
│ PacketSniffer   │ ← Scapy sniff()
│ (capture/)      │
└────────┬────────┘
         │ raw bytes
         ▼
┌─────────────────┐
│ PacketQueue     │ ← Thread-safe queue
│ (capture/)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ICDParser       │ ← Header parsing only
│ (parser/)       │   (payload pending ICD spec)
└────────┬────────┘
         │ ParseResult
         ▼
┌─────────────────┐
│ StatsCalculator │ ← PPS, Jitter, Loss
│ (analysis/)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LiveDataProvider│ ← Dashboard state
│ (data/)         │
└────────┬────────┘
         │ Dict
         ▼
┌─────────────────┐
│ Dash Callbacks  │ ← UI updates
│ (callbacks/)    │
└─────────────────┘
```

---

## 3. 파일별 상세 분석

### 3.1 진입점 (`run.py`)

**역할**: 통합 CLI 진입점

**주요 기능**:
- `--mode`: mock/live 모드 선택
- `--interface`: 네트워크 인터페이스 지정
- `--port`: 서버 포트 지정
- `--debug`: 디버그 모드 활성화

**코드 품질**:
```python
def resolve_mode(args) -> bool:
    """모드 결정 (CLI 인자 > 환경변수 > 기본값)."""
    if args.mode is not None:
        return args.mode == "live"
    env_live = os.getenv("UGV_MON_USE_LIVE", "").lower()
    return env_live == "true"
```
✅ **우수**: 우선순위 명확, 하위 호환성 유지

---

### 3.2 설정 관리 (`ugv_mon/config.py`)

**구조**:
```python
@dataclass
class Config:
    app: AppConfig           # 서버 설정
    network: NetworkConfig   # 캡처 설정
    ui: UIConfig             # UI 설정
    threshold: ThresholdConfig  # 임계값
```

**환경변수 지원**:
| 변수 | 설명 | 기본값 |
|------|------|--------|
| `UGV_MON_DEBUG` | 디버그 모드 | false |
| `UGV_MON_PORT` | 서버 포트 | 8050 |
| `UGV_MON_INTERFACE` | 캡처 인터페이스 | lo |
| `UGV_MON_POLL_INTERVAL` | 폴링 간격 (ms) | 2000 |

✅ **우수**: dataclass 활용, 환경변수 외부화

---

### 3.3 상수 정의 (`ugv_mon/constants.py`)

**내용**:
```python
# 장치 관련
DEVICE_IDS = ["vic", "rdc", "adc", ...]
DEVICE_NAMES = ["VIC", "RDC", "ADC", ...]

# ICD 관련
ICD_HEADER_SIZE = 12
ICD_CHECKSUM_SIZE = 2
ICD_MIN_PACKET_SIZE = 14

# 시퀀스 관련
MAX_SEQUENCE = 256
EXPECTED_PPS = 1000
```

✅ **우수**: 매직 넘버 제거, DRY 원칙 준수

---

### 3.4 ICD 파서 (`ugv_mon/parser/icd_parser.py`)

**헤더 구조** (12 bytes):
| 오프셋 | 크기 | 필드 |
|--------|------|------|
| 0-3 | 4 | timestamp |
| 3 | 1 | sequence (timestamp의 마지막 바이트) |
| 4 | 1 | source_id |
| 5 | 1 | dest_id |
| 6 | 1 | msg_code |
| 7 | 1 | ack_flag |
| 8-9 | 2 | reserved |
| 10-11 | 2 | data_length |

**체크섬 검증**:
```python
def _verify_checksum(self, data: bytes) -> bool:
    received = struct.unpack('<H', data[-2:])[0]
    calculated = sum(data[:-2]) & 0xFFFF
    return calculated == received
```

**파싱 통계**:
- `parse_count`: 전체 파싱 시도
- `success_count`: 성공 횟수
- `checksum_fail_count`: 체크섬 실패

✅ **우수**: 상수 활용, 통계 제공
⚠️ **주의**: 페이로드 파싱은 ICD 명세 확정 대기 중

---

### 3.5 통계 계산기 (`ugv_mon/analysis/stats_calculator.py`)

**제공 지표**:
| 지표 | 메서드 | 설명 |
|------|--------|------|
| PPS | `get_pps()` | 초당 패킷 수 |
| 평균 지터 | `get_average_jitter()` | 패킷 간 시간 차이 |
| P95/P99 | `get_jitter_percentiles()` | 백분위 지터 |
| 패킷 손실 | `get_packet_loss()` | 시퀀스 갭 기반 |
| 가용성 | `get_availability()` | 예상 대비 수신률 |

**시퀀스 롤오버 처리**:
```python
def _seq_gap(self, prev_seq: int, curr_seq: int) -> int:
    if curr_seq >= prev_seq:
        return curr_seq - prev_seq
    return (self._max_sequence - prev_seq) + curr_seq
```

✅ **우수**: 스레드 안전 (Lock), 롤오버 처리

---

### 3.6 데이터 제공자 (`ugv_mon/data/`)

**Mock vs Live 인터페이스**:
```python
class DataProviderProtocol(Protocol):
    def update_data(self, prev_data: Dict) -> Dict: ...
    def get_logs(self, limit: int = 50) -> List[Dict]: ...
    def clear_logs(self) -> None: ...
    @property
    def log_count(self) -> int: ...
```

**LiveDataProvider 추가 기능**:
- `start_capture()` / `stop_capture()`
- `switch_interface(new_interface)`
- `toggle_connection()`
- `get_available_interfaces()`

✅ **우수**: Protocol 기반 Duck Typing, 인터페이스 동적 조회

---

### 3.7 콜백 구조 (`ugv_mon/callbacks/update_callbacks.py`)

**콜백 그룹**:
| 함수 | 역할 |
|------|------|
| `_register_data_callback` | 데이터 폴링 (2초 간격) |
| `_register_component_callback` | UI 컴포넌트 업데이트 |
| `_register_control_callbacks` | 버튼 제어 (Pause, Clear) |
| `_register_ui_callbacks` | 인터페이스/연결 토글 |

**의존성 주입**:
```python
def register_callbacks(app, data_provider: DataProviderProtocol) -> None:
    """모든 대시보드 콜백 등록."""
    if data_provider is None:
        raise ValueError("data_provider cannot be None")
```

✅ **우수**: 클로저 패턴으로 전역 상태 제거

---

## 4. 테스트 분석

### 4.1 테스트 커버리지

| 파일 | 테스트 수 | 대상 |
|------|----------|------|
| `test_icd_parser.py` | 16개 | 헤더 파싱, 체크섬, 통계 |
| `test_stats_calculator.py` | 20개 | 지터, 손실, 롤오버, PPS |
| **합계** | **36개** | |

### 4.2 테스트 실행

```bash
# 단위 테스트
python -m pytest tests/ -v

# 통합 테스트 (패킷 캡처)
sudo python3 test_capture_packets.py
```

### 4.3 테스트 케이스 예시

**ICD 파서 테스트**:
```python
def test_checksum_verification_pass(self):
    """올바른 체크섬 검증."""
    header = bytes([0x10, 0x20, ...])
    checksum = sum(header) & 0xFFFF
    packet = header + struct.pack('<H', checksum)
    
    result = self.parser.parse(packet)
    
    assert result.checksum_ok is True
```

**통계 계산기 테스트**:
```python
def test_sequence_rollover_with_loss(self):
    """시퀀스 롤오버 + 손실."""
    self.calc.record_packet(now, sequence=254, size=100)
    self.calc.record_packet(now + delta, sequence=2, size=100)
    
    loss = self.calc.get_packet_loss()
    
    # 254 -> 2: gap = (256-254) + 2 = 4, loss = 3
    assert loss == 3
```

✅ **우수**: 엣지 케이스 (롤오버) 테스트 포함

---

## 5. 보안 분석

### 5.1 해결된 이슈

| 이슈 | 이전 | 현재 | 상태 |
|------|------|------|------|
| debug 기본값 | `True` | `False` | ✅ 해결 |
| 전역 상태 | 전역 변수 | 클로저 DI | ✅ 해결 |
| 리소스 누수 | 미처리 | `_cleanup_sniffer()` | ✅ 해결 |

### 5.2 주의 사항

| 항목 | 현재 상태 | 권장 |
|------|----------|------|
| `host` | `0.0.0.0` (모든 인터페이스) | 내부망 전용 확인 필요 |
| `sudo` 권한 | Live 모드에 필요 | `setcap` 권한 분리 권장 |
| 포트 하드코딩 | 50000→61000 | 환경변수로 외부화 고려 |

---

## 6. 코드 품질 점수

### 6.1 항목별 점수

| 항목 | 점수 | 근거 |
|------|------|------|
| **아키텍처** | 9/10 | 계층 분리 우수, Protocol 기반 DI |
| **가독성** | 8/10 | docstring 양호, 상수 중앙화 |
| **테스트** | 7/10 | 36개 테스트, 커버리지 도구 미사용 |
| **보안** | 7/10 | debug 수정됨, sudo 권한 분리 필요 |
| **에러 처리** | 7/10 | 기본 처리 양호, 복구 로직 미흡 |
| **유지보수성** | 9/10 | 모듈화 우수, 문서 충실 |
| **문서화** | 9/10 | 8개 문서, 트러블슈팅 가이드 |
| **일관성** | 8/10 | 스타일 모듈화, 일부 타입 힌트 누락 |

### 6.2 종합 점수

```
┌────────────────────────────────────────────────┐
│                                                │
│          종합 점수: 8.0 / 10                   │
│                                                │
│  ████████████████████████████████░░░░░░░░      │
│                                                │
│  현업 적용 가능 수준                            │
│  프로덕션 배포 전 소규모 개선 권장              │
│                                                │
└────────────────────────────────────────────────┘
```

---

## 7. 개선 권장 사항

### 7.1 즉시 적용 가능 (Low Effort)

#### 타입 힌트 보강
```python
# Before
def update_data(self, prev_data: Dict) -> Dict:

# After
from typing import TypedDict

class DashboardState(TypedDict):
    connected: bool
    interface: str
    capturePps: int
    # ...

def update_data(self, prev_data: DashboardState) -> DashboardState:
```

#### 테스트 커버리지 측정
```bash
pip install pytest-cov
python -m pytest tests/ --cov=ugv_mon --cov-report=html
```

### 7.2 중기 개선 (1개월 내)

#### ICD 페이로드 파싱 (명세 확정 시)
```python
# parser/models.py에 추가
@dataclass
class StatusPayload:
    operation_mode: OperationMode
    authority: Authority
    driving_state: DrivingState
    # ...
```

#### 에러 복구 메커니즘
```python
def _capture_loop(self) -> None:
    max_retries = 3
    retry_count = 0
    
    while self._running and retry_count < max_retries:
        try:
            sniff(...)
        except OSError as e:
            retry_count += 1
            logger.warning(f"Retry {retry_count}/{max_retries}: {e}")
            time.sleep(1)
```

### 7.3 장기 과제

1. **CI/CD 파이프라인**: GitHub Actions / GitLab CI
2. **모니터링 연동**: Prometheus + Grafana
3. **성능 프로파일링**: cProfile, memory_profiler

---

## 8. 이전 리뷰 대비 개선 현황

| 이전 지적 사항 | 상태 | 해결 방법 |
|---------------|------|----------|
| 진입점 3개 분리 | ✅ 해결 | `run.py` 통합 CLI |
| 전역 상태 사용 | ✅ 해결 | Protocol 기반 DI |
| `debug: True` 기본값 | ✅ 해결 | `False`로 변경 |
| 매직 넘버 산재 | ✅ 해결 | `constants.py` 생성 |
| 스타일 하드코딩 | ✅ 해결 | `styles.py` 생성 |
| 단위 테스트 부재 | ✅ 해결 | 36개 테스트 추가 |
| 리소스 누수 | ✅ 해결 | `_cleanup_sniffer()` |

> **결론**: 이전 코드 리뷰에서 지적된 Critical/Major 이슈의 **100%가 해결**되었습니다.

---

## 9. 결론

### 9.1 강점
- **아키텍처**: 관심사 분리가 잘 되어 있어 유지보수 용이
- **테스트**: 핵심 로직에 대한 단위 테스트 존재
- **문서화**: 개발자가 빠르게 온보딩 가능한 수준
- **확장성**: Mock/Live 전환이 용이한 설계

### 9.2 개선 필요
- **타입 안전성**: `TypedDict` 도입으로 런타임 에러 방지
- **에러 복구**: 네트워크 장애 시 자동 재연결
- **ICD 페이로드**: 명세 확정 후 구현 필요

### 9.3 최종 평가

```
현업 적용 가능 수준의 코드 품질.
ICD 명세 확정 후 페이로드 파싱만 추가하면 프로덕션 배포 가능.
```

---

*문서 작성일: 2026-01-27*
