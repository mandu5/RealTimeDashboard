# UGV-MON 프로젝트 종합 발표 자료

> 최종 수정: 2026-02-05  
> 발표자: [이름]  
> 대상: 팀장님 발표용

---

## 1. 프로젝트 개요

### 1.1. 과제 선정 배경

1.1.1. **문제 정의**
- 무인차량(UGV)과 통제시스템 간 통신 품질 모니터링 필요
- 기존에는 실시간 모니터링 도구 부재
- 통신 장애 발생 시 원인 파악 어려움

1.1.2. **과제 선택 이유**
- 실제 현장에서 사용 가능한 실용적 도구 개발
- 네트워크 프로그래밍 + 데이터 시각화 역량 강화
- Python 생태계 (Dash, Scapy, pandas) 학습

1.1.3. **프로젝트 목표**
- UDP 패킷 실시간 캡처 및 파싱
- KPI 대시보드 (PPS, 지터, 가용성 등) 시각화
- 이상 상황 감지 및 로깅

---

### 1.2. 기술 스택

| 영역 | 기술 | 선택 이유 |
|------|------|----------|
| 패킷 캡처 | Scapy | Python 네이티브, 필터링 유연성 |
| 웹 프레임워크 | Dash | 리액티브 UI, Python only |
| UI 컴포넌트 | Mantine | 모던 디자인, 다크모드 지원 |
| 데이터 분석 | pandas | 시계열 분석, 통계 계산 |
| 차트 | Plotly | 인터랙티브 그래프 |
| 테스트 | pytest | 단위/통합 테스트 |

---

### 1.3. 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│                        UGV-MON                               │
├─────────────────────────────────────────────────────────────┤
│   [Capture Layer]                                            │
│   └── PacketSniffer (Scapy) → PacketQueue → ICDParser        │
├─────────────────────────────────────────────────────────────┤
│   [Analysis Layer]                                           │
│   └── StatsCalculator (List + pandas) → KPI 계산             │
├─────────────────────────────────────────────────────────────┤
│   [Presentation Layer]                                       │
│   └── Dash App → dcc.Store → Callbacks → UI Components       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 기능 요구사항

### 2.1. 핵심 기능 (MVP)

| # | 기능 | 상태 |
|---|------|------|
| F1 | UDP 패킷 실시간 캡처 | ✅ 완료 |
| F2 | ICD v1.0 프로토콜 파싱 | ✅ 완료 |
| F3 | KPI 대시보드 (PPS, 지터, 가용성) | ✅ 완료 |
| F4 | 연결 상태 표시 | ✅ 완료 |
| F5 | 로그/이벤트 테이블 | ✅ 완료 |

### 2.2. 확장 기능 (Phase 1-6)

| # | 기능 | 상태 |
|---|------|------|
| E1 | pandas 기반 데이터 분석 | ✅ 완료 |
| E2 | 가용성 요약 통계 (10분/1시간) | ✅ 완료 |
| E3 | msg_code별 통계 탭 | ✅ 완료 |
| E4 | 연결 이력 로그 | ✅ 완료 |
| E5 | 운용상태 전이 분석 | ✅ 완료 |
| E6 | 비상정지 원인 통계 | ✅ 완료 |

---

## 3. 개발 타임라인

### 3.1. 1주차: 환경 구축 및 기초

- 개발 환경 설정 (Python, Dash, Scapy)
- ICD 프로토콜 분석 및 문서화
- Mock 데이터 생성기 구현
- 기본 대시보드 레이아웃

### 3.2. 2주차: 패킷 캡처 구현

- PacketSniffer 클래스 구현
- PacketQueue (스레드 안전) 설계
- ICDParser 파싱 로직
- Live/Mock 모드 전환

### 3.3. 3주차: KPI 및 시각화

- StatsCalculator 통계 계산기
- PPS, 지터, 패킷손실 계산
- Plotly 차트 구현
- KPI 카드 컴포넌트

### 3.4. 4주차: UI 고도화

- 운용상태 패널 (모드, 권한, 주행상태)
- 비상정지 인디케이터
- 장치 연결 상태 그리드
- 가용성 타임라인

### 3.5. 5주차: 데이터 분석 확장

- 중간 발표 피드백 반영
- pandas 하이브리드 전환
- 6개 분석 기능 Phase 완료
- 최종 문서화

---

## 4. 핵심 기술 구현

### 4.1. 패킷 캡처 (sniffer.py)

```python
# Scapy 기반 UDP 패킷 캡처
def _run_capture(self):
    sniff(
        iface=self._interface,
        filter=f"udp port {self._src_port}",
        prn=self._process_packet,
        store=False,
    )

def _process_packet(self, packet):
    if Raw in packet:
        capture_time = datetime.now()
        raw_data = bytes(packet[Raw].load)
        self._callback((capture_time, raw_data))
```

### 4.2. ICD 파싱 (icd_parser.py)

```python
# 헤더 구조: Timestamp(4) + MsgID(2) + Reserved(2) + DataLen(2)
def parse_header(self, data: bytes) -> Optional[ICDHeader]:
    if len(data) < 10:
        return None
    timestamp, msg_id, reserved, data_len = struct.unpack(">IHHH", data[:10])
    sequence = timestamp & 0x0F  # 하위 4비트
    return ICDHeader(timestamp, msg_id, reserved, data_len, sequence)
```

### 4.3. Dash 콜백 (update_callbacks.py)

```python
@callback(
    Output("dashboard-data", "data"),
    Input("interval-component", "n_intervals"),
    State("is-paused", "data"),
)
def update_data(n, is_paused):
    if is_paused:
        return no_update
    return provider.get_current_data()
```

### 4.4. 통합 저장소 (packet_store.py)

```python
# 단일 deque에 모든 PacketRecord 저장, 용도별 변환 제공
class PacketStore:
    def add(self, record: PacketRecord) -> Optional[float]:
        # 지터 계산 + 패킷 손실 추적 + deque 저장
        ...

    def get_stats_dict(self) -> Dict:
        # PPS, 지터, 손실, 가용성 등 KPI 통계
        ...

    def get_chart_data(self, limit=180) -> List[Dict]:
        # 차트 표시용 시계열 데이터
        ...
```

---

## 5. 데이터 흐름

```
[네트워크]
    │
    ▼
[PacketSniffer] ─── bytes (raw packet)
    │
    ▼
[PacketQueue] ─── (timestamp, bytes)
    │
    ▼
[PacketProcessor] ─── 파싱 + PacketStore 저장
    │
    ▼
[PacketStore] ─── deque[PacketRecord] (단일 저장소)
    │
    ▼
[LiveDataProvider._build_dashboard_data()]
    │
    ▼
[dcc.Store("dashboard-data")] ─── JSON (Dict)
    │
    ▼
[Dash Callbacks] ─── 자동 트리거
    │
    ▼
[UI Components] ─── 화면 렌더링
```

---

## 6. KPI 정의

| KPI | 정의 | 계산 방식 |
|-----|------|----------|
| PPS | Packets Per Second | 최근 1초 내 패킷 수 |
| 지터 | 패킷 간격 변동 | \|현재 interval - 이전 interval\| |
| 가용성 | 정상 통신 비율 | (수신 패킷 / 예상 패킷) × 100 |
| 패킷손실 | 누락된 패킷 수 | 시퀀스 번호 갭 합계 |

---

## 7. 테스트 현황

### 7.1. 단위 테스트

| 모듈 | 테스트 수 | 커버리지 |
|------|----------|----------|
| icd_parser | 8+ | ICD 파싱 검증 |

### 7.2. 테스트 실행

```bash
$ python -m pytest tests/ -v
```

---

## 8. 프로젝트 구조

```
ugv_mon/
├── core/
│   ├── models.py              # 통합 데이터 모델
│   ├── config.py              # 앱 설정
│   └── constants.py           # 상수 정의
├── capture/
│   ├── sniffer.py             # 패킷 캡처
│   ├── queue.py               # 스레드 안전 큐
│   └── packet_processor.py    # 처리 파이프라인
├── parser/
│   └── icd_parser.py          # ICD 파싱 (비트마스킹)
├── data/
│   ├── packet_store.py        # 통합 저장소 (단일 deque)
│   ├── live_provider.py       # 실시간 데이터 제공
│   └── mock_data.py           # 모의 데이터
├── layouts/
│   ├── main_layout.py         # 메인 레이아웃
│   ├── panels.py              # UI 패널들
│   └── charts.py              # 차트 컴포넌트
├── callbacks/
│   └── update_callbacks.py    # Dash 콜백
├── components/                 # 재사용 컴포넌트
├── config.py                   # 설정 관리
└── styles.py                   # 스타일 정의

docs/                           # 문서
tests/                          # 테스트
```

---

## 9. 실행 방법

### 9.1. Mock 모드 (개발/테스트)

```bash
python run.py
# 브라우저: http://localhost:8050
```

### 9.2. Live 모드 (실제 캡처)

```bash
sudo UGV_MON_USE_LIVE=1 UGV_MON_INTERFACE=en0 python run.py
```

---

## 10. 주요 성과

### 10.1. 정량적 성과

- 코드 라인: ~3,000줄
- 테스트: 33개 통과
- 문서: 10개 파일
- 개발 기간: 5주

### 10.2. 정성적 성과

- 실시간 모니터링 도구 완성
- 확장 가능한 아키텍처 설계
- 포괄적인 문서화
- 테스트 기반 개발

---

## 11. 향후 계획

### 11.1. 단기 (1-2주)

- 실제 UGV 연동 테스트
- 성능 최적화
- 사용자 피드백 반영

### 11.2. 중기 (1개월)

- 알람/알림 기능
- 데이터 내보내기 (CSV, Excel)
- 리포트 생성

### 11.3. 장기 (3개월+)

- 다중 UGV 모니터링
- DB 연동 (장기 데이터 저장)
- 웹 배포 (Docker)

---

## 12. Q&A

*(발표 후 질의응답)*

---

## 첨부: 스크린샷

*(대시보드 실행 화면 캡처 추가)*
