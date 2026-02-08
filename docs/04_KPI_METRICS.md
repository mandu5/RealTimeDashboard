# UGV-MON KPI 정의 및 분석

> **최종 업데이트**: 2026-02-08

## 개요

UGV-MON은 8개의 핵심 KPI를 실시간으로 계산하고 표시합니다. 모든 계산은 `packet_store.py`의 `PacketStore` 클래스에서 수행됩니다.

---

## 1. 수신 PPS (Packets Per Second)

### 정의

초당 캡처되는 패킷 수

### 계산 방법

```python
# packet_store.py - get_pps()
def get_pps(self) -> int:
    now = datetime.now()
    one_sec_ago = now - timedelta(seconds=1)
    return sum(1 for r in self._records if r.timestamp >= one_sec_ago)
```

### 예상값

- 정상: ~3 pps (0x01, 0x25, 0x40 각각 1개/초)

---

## 2. 필터 통과율 (Filter Pass %)

### 정의

BPF 필터를 통과한 패킷의 비율

### 계산 방법

```python
# capture/stats.py에서 집계
filter_pass = (filtered_packets / total_captured) * 100
```

### 예상값

- 정상: 100% (모든 UDP 패킷이 필터 통과)

---

## 3. 파싱 성공률 (Parse Success %)

### 정의

ICD 구조로 정상 파싱된 패킷의 비율

### 계산 방법

```python
# packet_store.py - get_parse_success_rate()
success_count = sum(1 for r in self._records if r.parse_ok)
return (success_count / total_count) * 100
```

### 파싱 실패 원인

| 원인                | 설명               |
| ------------------- | ------------------ |
| 헤더 길이 부족      | 12바이트 미만      |
| 알 수 없는 msg_code | 정의되지 않은 코드 |
| payload 구조 오류   | 예상 구조와 불일치 |

---

## 4. 체크섬 오류율 (Checksum Fail %)

### 정의

파싱은 성공했지만 체크섬 검증에 실패한 패킷의 비율

### 계산 방법

```python
# packet_store.py - get_checksum_fail_rate()
fail_count = sum(1 for r in self._records if not r.checksum_ok)
return (fail_count / total_count) * 100
```

### 예상값

- 정상: 0% (모든 패킷 체크섬 정상)

---

## 5. 패킷 손실 (Packet Loss)

### 정의

시퀀스 번호 기준 누락된 패킷 수

### 계산 방법

```python
# packet_store.py - get_packet_loss()
# 시퀀스 갭 합계 계산
# 예: 시퀀스 1, 2, 5, 6 → 3, 4 누락 → 손실 2개
```

### 시퀀스 번호

- ICD 헤더 timestamp 하위 4비트 (0~15)
- 16에서 wrap-around 처리

---

## 6. 가용성 (Availability %)

### 정의

통신이 정상적으로 유지된 시간의 비율

### 계산 방법

```python
# packet_store.py - get_availability()
TIMEOUT_SEC = 1.5  # 1.5초 이내 패킷 수신 시 "연결됨"

connected_time = 0.0
for i in range(len(records) - 1):
    gap = (records[i+1].timestamp - records[i].timestamp).total_seconds()
    if gap <= TIMEOUT_SEC:
        connected_time += gap

availability = (connected_time / actual_duration) * 100
```

### 예시

```
시간:    0초    1초    2초    3초    4초    5초
패킷:     ●      ●      ●      ✗      ●      ●
간격:     └─1초─┘ └─1초─┘ └─2초─┘ └─1초─┘
               ✓       ✓       ✗       ✓

connected_time = 1 + 1 + 0 + 1 = 3초
availability = 3/5 × 100 = 60%
```

### 윈도우

- 5분 (300초): 기본 표시
- 1시간 (3600초): hourly 배지

---

## 7. 지터 - 현재 (Current Jitter)

### 정의

가장 최근 패킷의 간격 변동

### 계산 방법

```python
지터 = |현재 간격 - 이전 간격|
```

### 예시

```
시간:    0ms   1000ms   1002ms   2001ms
패킷:     ●       ●        ●        ●
간격:     └─1000─┘ └───2───┘ └─999──┘

지터1 = |2 - 1000| = 998ms  (첫 계산 - 이전 간격 없음)
지터2 = |999 - 2| = 997ms   ← 현재 지터
```

---

## 8. 지터 P95 (Jitter P95)

### 정의

지터의 95번째 백분위 값 (상위 5% 제외)

### 계산 방법

```python
# packet_store.py - get_jitter_p95()
jitters = [r.jitter_ms for r in self._records if r.jitter_ms is not None]
sorted_jitters = sorted(jitters)
n = len(sorted_jitters)
p95_idx = min(int(n * 0.95), n - 1)
return sorted_jitters[p95_idx]
```

### P95를 사용하는 이유

- 이상치(상위 5%) 제외
- 네트워크의 "일반적인" 안정성 파악
- 일시적 스파이크에 덜 민감

---

## Timestamp 구분

### 두 가지 Timestamp

| 구분          | ICD 헤더 timestamp       | 캡처 timestamp          |
| ------------- | ------------------------ | ----------------------- |
| **위치**      | 패킷 데이터 [0:4] 바이트 | Python `datetime.now()` |
| **생성 시점** | VIC 송신 시              | 우리 시스템 수신 시     |
| **용도**      | 시퀀스 추출 (하위 4비트) | **지터/가용성 계산**    |

---

## msg_code별 분리 계산

### 이유

0x01, 0x25, 0x40 메시지는 각각 다른 주기로 송신되므로 별도 계산 필요

```python
# packet_store.py 내부
self._last_by_code: Dict[int, Dict]  # msg_code별 마지막 timestamp/interval
```

### msg_code 종류

| 코드 | 명칭      | 주기 |
| ---- | --------- | ---- |
| 0x01 | 상태 보고 | 1초  |
| 0x25 | 확장 상태 | 1초  |
| 0x40 | 장치 상태 | 1초  |

---

## 데이터 저장 구조

### PacketRecord

```python
@dataclass
class PacketRecord:
    timestamp: datetime       # 캡처 시각
    msg_code: int             # 메시지 코드
    sequence: int             # 시퀀스 번호
    size: int                 # 패킷 크기
    jitter_ms: Optional[float]    # 지터 (ms)
    interval_ms: Optional[float]  # 간격 (ms)
    parse_ok: bool            # 파싱 성공
    checksum_ok: bool         # 체크섬 성공
    operation_mode: str       # 운용 모드
    authority: str            # 운용 권한
```

### 저장소

```python
# packet_store.py
self._records: deque[PacketRecord]  # 최대 1시간 보관 (360,000개)
```
