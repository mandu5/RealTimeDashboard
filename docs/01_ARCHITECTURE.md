# UGV-MON 아키텍처 구조

---

## CSCI/CSC/CSU 구조

### 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                     CSCI: UGV-MON                           │
│           VIC↔OCS Real-time Communication Monitoring        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   CSC-001     │     │   CSC-002     │     │   CSC-003     │
│ Data          │     │ Data          │     │ Data          │
│ Acquisition   │     │ Processing/   │     │ Presentation  │
│ (데이터 수집) │     │ Analysis      │     │ (데이터 전시) │
├───────────────┤     │(데이터처리/분석)│     ├───────────────┤
│ • 실시간      │     │               │     │ • 상태 전시   │
│   데이터 수집 │     │ • ICD 파싱    │     │ • 로그/이벤트 │
│ • 데이터      │     │ • 데이터 품질 │     │   전시        │
│   필터링      │     │   분석        │     │ • 성능 지표   │
│               │     │ • 운용 데이터 │     │   전시        │
│               │     │   분석        │     │               │
└───────────────┘     └───────────────┘     └───────────────┘
```

### 코드 매핑

| CSC | CSU | Python 모듈 | 구현 일정 |
|-----|-----|-------------|----------|
| CSC-001 | 실시간 데이터 수집 | `ugv_mon/capture/sniffer.py` | Day 2 |
| CSC-001 | 데이터 필터링 | `ugv_mon/capture/filter.py` | Day 2 |
| CSC-002 | ICD 파싱 | `ugv_mon/parser/` | Day 3 |
| CSC-002 | 데이터 품질 분석 | `ugv_mon/analysis/quality.py` | Day 4 |
| CSC-002 | 운용 데이터 분석 | `ugv_mon/analysis/operational.py` | Day 5-6 |
| CSC-003 | 상태 전시 | `ugv_mon/layouts/panels.py` | Day 1 |
| CSC-003 | 로그/이벤트 전시 | `ugv_mon/components/log_table.py` | Day 1 |
| CSC-003 | 성능 지표 전시 | `ugv_mon/components/kpi_card.py`, `layouts/charts.py` | Day 1, 8 |

---

## 데이터 흐름

### 전체 파이프라인

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Network  │───▶│  Scapy   │───▶│   ICD    │───▶│ Analysis │───▶│   Dash   │
│Interface │    │ Capture  │    │  Parser  │    │  Module  │    │Dashboard │
│(lo/eno2) │    │ +Filter  │    │          │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
  UDP 패킷      필터링된        파싱된 상태      분석 결과       시각화된 UI
              패킷 스트림      (모드/권한/      (KPI/지터/       
                              장치/비상)       가용성)
```

### 폴링 사이클

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ dcc.Interval │────▶│ update_      │────▶│ dashboard-   │
│ (2초마다)    │     │ dashboard_   │     │ data Store   │
│              │     │ data()       │     │ 갱신         │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ UI 컴포넌트  │◀────│ update_all_  │◀────│ dashboard-   │
│ 갱신         │     │ components() │     │ data 변경    │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 상태 관리

### dcc.Store 구조

대시보드의 모든 상태는 `dcc.Store("dashboard-data")`에 JSON 형식으로 저장됩니다.

```python
{
    # 연결 정보
    "connected": true,
    "interface": "lo",
    "filter": "50000→61000",
    "lastPacketTime": "14:32:05",
    
    # KPI 메트릭
    "capturePps": 1024,
    "filterPass": 99.9,
    "parseSuccess": 100.0,
    "checksumFail": 0.0,
    "packetLoss": 0,
    "availability5min": 99.98,
    "availability1hour": 99.99,
    "jitterP95": 2.1,
    "jitterP99": 2.4,
    
    # 운용 상태
    "operationalMode": "원격 주행 (REMOTE)",
    "operationalAuthority": "OCS(운용통제기)",
    "drivingState": "전진/대기",
    
    # 컬렉션
    "devices": [...],           # 10개 장치 상태 (error_reason 포함)
    "emergencyStatus": {...},   # 10개 비상정지 원인
    "combinedData": [...],      # 60개 차트 데이터 포인트
    "availabilitySegments": [...]  # 가용성 타임라인 세그먼트
}

# 추가 Store
- "chart-time-range": 시간 범위 선택 (30, 60, 300초)
```

---

## 설계 결정 사항

### 왜 Polling (dcc.Interval)인가?

1. **단순성**: `dcc.Interval`은 내장 기능이며 문서화가 잘 되어 있음
2. **안정성**: WebSocket 연결 관리 복잡도가 없음
3. **충분한 실시간성**: 2초 갱신으로 모니터링 목적에 충분
4. **개발 속도**: 인턴십 일정 내 빠른 구현 가능

### 왜 Scapy인가?

1. **개발 리스크 감소**: raw socket보다 높은 추상화 수준
2. **내장 필터링**: BPF 필터 문법 지원
3. **크로스 플랫폼**: loopback/물리 인터페이스 모두 지원
4. **디버깅 용이성**: 개발 중 패킷 검사 용이

### 왜 통계/규칙 분석인가? (ML 대신)

1. **데이터 특성**: ICD v1.0 데이터는 bitfield 중심 (이산 데이터)
2. **라벨 부재**: 지도학습용 정답 데이터가 없음
3. **검증 가능성**: 통계 지표는 즉시 설명/검증 가능
4. **일정 리스크**: 8주 일정에서 ML 성능 보장 어려움

---

## 기술 스택 세부

| 계층 | 기술 | 목적 |
|------|------|------|
| 캡처 | Scapy | 패킷 스니핑 및 필터링 |
| 처리 | Python 3.10 | ICD 파싱, 분석 |
| 상태 | dcc.Store | 메모리 내 상태 관리 |
| 폴링 | dcc.Interval | 2초 업데이트 주기 |
| UI | Dash + DMC | 대시보드 프레임워크 |
| 차트 | Plotly | 시계열 시각화 |
| 테이블 | AG-Grid | 고성능 로그 테이블 |
