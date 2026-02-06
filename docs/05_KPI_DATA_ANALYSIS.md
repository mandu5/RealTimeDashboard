# UGV-MON KPI 상세 설명서

> **최종 업데이트**: 2026-02-04  
> **목적**: 멘토님 발표용 자료 - 각 KPI의 정의, 계산 방식, 데이터 흐름을 완벽하게 이해할 수 있도록 작성

---

## 📌 목차

1. [Timestamp에 대한 이해](#1-timestamp에-대한-이해)
2. [캡처 PPS](#2-캡처-pps-packets-per-second)
3. [파싱 성공률](#3-파싱-성공률-parse-success-)
4. [체크섬 실패율](#4-체크섬-실패율-checksum-fail-)
5. [패킷 손실](#5-패킷-손실-packet-loss)
6. [가용성](#6-가용성-availability-)
7. [지터](#7-지터-jitter-p95)
8. [수정 전/후 비교](#8-수정-전후-비교)

---

## 1. Timestamp에 대한 이해

### 🔑 핵심: 두 개의 다른 timestamp가 있다!

| 구분 | ICD 헤더 timestamp | 캡처 timestamp |
|------|-------------------|----------------|
| **위치** | 패킷 데이터 [0:4] 바이트 | 파이썬 코드에서 생성 |
| **생성 시점** | VIC/송신측에서 패킷 만들 때 | 우리 시스템이 패킷 받을 때 |
| **값 예시** | `4f000000` → 79 | `datetime.now()` |
| **용도** | 송신측 시간/카운터 | **지터/가용성 계산에 사용** |

---

### 1.1 ICD 헤더 timestamp (`4f000000`)

```python
# 패킷 데이터에서 추출하는 방법
raw_data = b'\x4f\x00\x00\x00...'
timestamp = struct.unpack('<I', raw_data[0:4])[0]  # Little Endian uint32
# 결과: 79
```

**이 값의 의미:**
- VIC/송신측에서 부여한 **카운터 또는 틱(tick)** 값으로 추정
- 실제 시간(epoch)이 아닐 가능성이 높음 (79, 128 같은 작은 값)
- 단위가 뭔지(ms? 10ms? 틱?)는 **멘토님께 확인 필요**

> ⚠️ **멘토님이 "이상하게 찍힌다"고 한 이유:**
> - 실제 시간이면 `1705312345000` 같은 큰 숫자여야 함
> - 79, 128 같은 작은 값은 "시간"이 아니라 "카운터"로 보임

---

### 1.2 캡처 timestamp (`datetime.now()`)

```python
# sniffer.py에서 패킷 받을 때 생성
capture_time = datetime.now()  # 예: 2024-01-15 14:30:25.123456
```

**이 값의 용도:**
- ✅ **지터 계산**: 패킷 간 도착 간격 변동 측정
- ✅ **가용성 계산**: 패킷이 얼마나 규칙적으로 오는지 판단
- ✅ **로그 기록**: 언제 패킷을 받았는지 표시

---

## 2. 캡처 PPS (Packets Per Second)

### 📖 의미
**초당 캡처되는 패킷 수** - 네트워크에서 얼마나 많은 패킷이 들어오는지 보여줌

---

### 🧮 계산 방법

```python
# stats_calculator.py - get_pps()
def get_pps(self) -> int:
    with self._lock:
        now = datetime.now()
        one_sec_ago = now - timedelta(seconds=1)
        
        # 최근 1초 내 패킷 수 카운트
        count = sum(1 for r in self._records if r.timestamp >= one_sec_ago)
        return count
```

**간단히 말하면:**
```
최근 1초 동안 받은 패킷 개수 세기
```

---

### 🔄 데이터 흐름 (패킷이 어디서 어디로 가는지)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. sniffer.py: 네트워크에서 패킷 캡처                             │
│    → callback((capture_time, raw_data))                         │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. queue.py: 큐에 저장 (중복 제거)                                │
│    → self._queue.append(packet)                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. live_provider.py: 큐에서 꺼내서 처리                           │
│    → _process_packet(raw, capture_time)                         │
│    → stats_calc.record_packet(capture_time, seq, size, msg_code)│
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. stats_calculator.py: 패킷 기록 저장                            │
│    → self._records.append(PacketRecord(...))                    │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. get_pps(): 최근 1초 내 records 개수 반환                        │
│    → sum(1 for r in self._records if r.timestamp >= one_sec_ago)│
└─────────────────────────────────────────────────────────────────┘
```

---

### 💾 저장 위치

```python
# stats_calculator.py
self._records: deque[PacketRecord]  # 모든 패킷 기록 저장 (최대 5분=300초분)
```

---

### 📊 현재 결과
- **예상값: ~3 pps** (1초마다 3개 패킷: 0x01, 0x25, 0x40)

---

## 3. 파싱 성공률 (Parse Success %)

### 📖 의미
**수신한 패킷 중 ICD 구조로 정상 파싱된 비율**

패킷이 들어왔을 때, 우리가 정의한 ICD 포맷대로 해석할 수 있는지 확인하는 것

---

### 🧮 계산 방법

```
파싱 성공률 = (파싱 성공 패킷 수 ÷ 전체 수신 패킷 수) × 100
```

```python
# live_provider.py
"parseSuccess": round((self._parse_success / max(self._total_packets, 1)) * 100, 1)
```

---

### 🔍 데이터는 어디서 오나?

#### 전체 수신 패킷 수 (`self._total_packets`):
```python
# live_provider.py - _process_packet()
def _process_packet(self, raw: bytes, capture_time: datetime):
    self._total_packets += 1  # ← 패킷 받을 때마다 +1
    result = self._parser.parse(raw)
    # ...
```

#### 파싱 성공 패킷 수 (`self._parse_success`):
```python
# live_provider.py - _process_packet()
def _process_packet(self, raw: bytes, capture_time: datetime):
    self._total_packets += 1
    result = self._parser.parse(raw)
    
    if result.success:        # ← 파싱 성공하면
        self._parse_success += 1  # ← +1
```

---

### ❌ 파싱 실패 원인

| 원인 | 설명 |
|------|------|
| 헤더 길이 부족 | 12바이트 미만 |
| 알 수 없는 msg_code | 정의되지 않은 코드 |
| payload 구조 오류 | 예상 구조와 불일치 |
| 데이터 손상 | 네트워크 오류 등 |

---

### 💾 저장 위치

```python
# live_provider.py
self._total_packets: int = 0   # 전체 패킷 수
self._parse_success: int = 0   # 파싱 성공 수
```

---

### 📊 현재 결과
- **100%** (모든 패킷이 정상 파싱됨)

---

## 4. 체크섬 실패율 (Checksum Fail %)

### 📖 의미
**파싱은 성공했지만 체크섬 검증에 실패한 패킷의 비율**

체크섬은 데이터가 전송 중 손상되지 않았는지 확인하는 값

---

### 🧮 계산 방법

```
체크섬 실패율 = (체크섬 실패 패킷 수 ÷ 전체 수신 패킷 수) × 100
```

```python
# live_provider.py
"checksumFail": round((self._checksum_fail / max(self._total_packets, 1)) * 100, 1)
```

---

### 🔍 데이터는 어디서 오나?

#### 체크섬 실패 패킷 수 (`self._checksum_fail`):
```python
# live_provider.py - _process_packet()
def _process_packet(self, raw: bytes, capture_time: datetime):
    self._total_packets += 1
    result = self._parser.parse(raw)
    
    if result.success:
        self._parse_success += 1
    if not result.checksum_ok:    # ← 체크섬 실패하면
        self._checksum_fail += 1  # ← +1
```

---

### 🆚 파싱 성공률 vs 체크섬 실패율 차이

```
전체 패킷 100개
│
├── 파싱 실패: 5개 (구조 오류)
│   └→ 파싱 성공률 = 95%
│
└── 파싱 성공: 95개
    │
    ├── 체크섬 실패: 2개 (데이터 손상)
    │   └→ 체크섬 실패율 = 2%
    │
    └── 체크섬 성공: 93개 (완전 정상) ✅
```

---

### 💾 저장 위치

```python
# live_provider.py
self._checksum_fail: int = 0   # 체크섬 실패 수
```

---

### 📊 현재 결과
- **0%** (모든 패킷의 체크섬이 정상)

---

## 5. 패킷 손실 (Packet Loss)

### 📖 의미
**시퀀스 번호 기준 누락된 패킷 수**

송신측에서 1, 2, 3, 4, 5 순서로 보냈는데 우리가 1, 2, 5만 받으면 3, 4가 손실된 것

---

### 🧮 계산 방법

```python
# stats_calculator.py
def get_packet_loss(self) -> int:
    # 예상 시퀀스와 실제 시퀀스의 갭 합계
    # 예: 시퀀스 1, 2, 5, 6 → 3, 4 누락 → 손실 2개
```

---

### ⚠️ 현재 상태

| 상태 | 설명 |
|------|------|
| **계산 불가** | 시퀀스 번호가 항상 0으로 오고 있음 |
| **해결 방법** | 멘토님께 시퀀스 번호 활성화 확인 필요 |

---

### 🔢 시퀀스 번호란?

```python
# ICD 헤더에서 추출
# timestamp 4바이트 중 마지막 1바이트가 sequence
sequence = data[3]  # 예: 0x00 → 0
```

---

## 6. 가용성 (Availability %)

### 📖 의미
**통신이 정상적으로 유지된 시간의 비율**

쉽게 말해: "패킷이 규칙적으로 잘 오고 있는가?"

---

### 🧮 계산 방법

```
가용성 = (연결 유지 시간 ÷ 측정 구간) × 100
```

---

### 🔍 데이터는 어디서 오나? (상세 설명)

```python
def get_availability(self, window_sec: Optional[int] = None) -> float:
    with self._lock:
        # ──────────────────────────────────────────────────────
        # 1단계: 윈도우 내 패킷 필터
        # ──────────────────────────────────────────────────────
        records_in_window = [r for r in self._records if r.timestamp >= cutoff]
        
        # ──────────────────────────────────────────────────────
        # 2단계: 측정 구간 계산
        # ──────────────────────────────────────────────────────
        first_packet_time = records_in_window[0].timestamp
        actual_duration = (now - first_packet_time).total_seconds()
        # 예: 첫 패킷이 10초 전에 왔다면 actual_duration = 10초
        
        # ──────────────────────────────────────────────────────
        # 3단계: 연결 시간 계산
        # ──────────────────────────────────────────────────────
        TIMEOUT_SEC = 1.5  # 1.5초 이내 패킷 오면 "연결됨"으로 간주
        
        connected_time = 0.0
        for i in range(len(records_in_window) - 1):
            # 패킷 간 간격 계산
            gap = (records_in_window[i + 1].timestamp - records_in_window[i].timestamp).total_seconds()
            
            if gap <= TIMEOUT_SEC:
                connected_time += gap  # 간격이 1.5초 이내면 연결 시간에 포함
        
        # ──────────────────────────────────────────────────────
        # 4단계: 마지막 패킷 ~ 현재까지도 계산
        # ──────────────────────────────────────────────────────
        last_gap = (now - records_in_window[-1].timestamp).total_seconds()
        if last_gap <= TIMEOUT_SEC:
            connected_time += last_gap
        
        # ──────────────────────────────────────────────────────
        # 5단계: 가용성 계산
        # ──────────────────────────────────────────────────────
        availability = (connected_time / actual_duration) * 100
```

---

### 📊 예시로 이해하기

```
시간:    0초    1초    2초    3초    4초    5초
패킷:     ●      ●      ●      ✗      ●      ●
         │      │      │      │      │      │
간격:     └─1초─┘ └─1초─┘ └─1초─┘ └─1초─┘
                  ✓      ✓      ✗      ✓

✓ = 1.5초 이내 (연결됨)
✗ = 1.5초 초과 (끊김으로 판단)

connected_time = 1 + 1 + 0 + 1 = 3초
actual_duration = 5초
가용성 = 3/5 × 100 = 60%
```

---

### ❓ TIMEOUT_SEC = 1.5초인 이유

| 이유 | 설명 |
|------|------|
| 패킷 주기 | 패킷이 약 1초마다 옴 |
| 여유 | 약간의 네트워크 지연 허용 |
| 판단 기준 | 1.5초 이내에 다음 패킷 안 오면 "끊김" |

---

### 💾 저장 위치

```python
# stats_calculator.py
self._records: deque[PacketRecord]  # 패킷 기록 (timestamp 포함)
```

---

### 📊 현재 결과
- **~100%** (패킷이 규칙적으로 잘 오고 있음)

---

## 7. 지터 (Jitter P95)

### 📖 의미
**패킷 도착 간격의 변동 정도** - 네트워크 안정성 지표

쉽게 말해: "패킷이 일정한 간격으로 오는가, 들쑥날쑥하는가?"

---

### 🎯 지터란?

```
지터 = |현재 간격 - 이전 간격|
```

---

### 📊 예시로 이해하기

```
시간:    0ms   1000ms   2002ms   3001ms
패킷:     ●       ●        ●        ●
         │       │        │        │
간격:     └─1000─┘└─1002──┘└─999───┘
                    ↑         ↑
                 간격1     간격2

지터1 = |1002 - 1000| = 2ms
지터2 = |999 - 1002| = 3ms
```

**해석:**
- 지터가 낮을수록 → 네트워크 안정적 (패킷이 규칙적으로 옴)
- 지터가 높을수록 → 네트워크 불안정 (패킷 간격이 들쑥날쑥)

---

### P95란?

| 지표 | 의미 |
|------|------|
| **P95** | 95%의 지터가 이 값 이하 (상위 5% 제외) |

**예시:**
```
지터 100개 측정: [1, 1, 2, 1, 2, 1, 3, 2, 1, 50, ...]
                                              ↑
                                          이상치(상위 1%)

P95 = 3ms  (대부분의 지터는 3ms 이하)
```

---

### 🔍 데이터는 어디서 오나? (상세 설명)

```python
# stats_calculator.py - record_packet()
def record_packet(self, timestamp: datetime, sequence: int, size: int, msg_code: int = 0) -> Optional[float]:
    with self._lock:
        jitter_ms = None
        
        # ──────────────────────────────────────────────────────
        # 1단계: msg_code별 저장소 확인/생성
        # ──────────────────────────────────────────────────────
        # 왜 msg_code별로? → 0x01, 0x25, 0x40 각각 따로 지터 계산
        if msg_code not in self._last_by_code:
            self._last_by_code[msg_code] = {"timestamp": None, "interval": None}
        
        code_data = self._last_by_code[msg_code]
        
        # ──────────────────────────────────────────────────────
        # 2단계: 이전 패킷이 있으면 간격 계산
        # ──────────────────────────────────────────────────────
        if code_data["timestamp"] is not None:
            # 현재 간격 = 현재 시간 - 이전 시간
            interval_ms = (timestamp - code_data["timestamp"]).total_seconds() * 1000
            
            # ──────────────────────────────────────────────────
            # 3단계: 이전 간격이 있으면 지터 계산
            # ──────────────────────────────────────────────────
            if code_data["interval"] is not None:
                # 지터 = |현재 간격 - 이전 간격|
                jitter_ms = abs(interval_ms - code_data["interval"])
            
            # 현재 간격을 다음 계산을 위해 저장
            code_data["interval"] = interval_ms
        
        # 현재 시간을 다음 계산을 위해 저장
        code_data["timestamp"] = timestamp
        
        # 기록 저장
        self._records.append(PacketRecord(timestamp, sequence, size, jitter_ms))
        return jitter_ms
```

---

### P95 계산 방법

```python
# stats_calculator.py
def get_jitter_percentiles(self) -> Tuple[float, float]:
    with self._lock:
        # 지터 값만 추출 (None 제외)
        jitters = [r.jitter_ms for r in self._records if r.jitter_ms is not None]
        
        if not jitters:
            return (0.0, 0.0)

        # 정렬
        sorted_jitters = sorted(jitters)  # 예: [0, 1, 1, 2, 2, 3, 5, 10]
        n = len(sorted_jitters)
        
        # P95 = 95% 위치의 값
        p95 = sorted_jitters[min(int(n * 0.95), n - 1)]
        
        return round(p95, 2)
```

---

### 💾 저장 위치

```python
# stats_calculator.py
self._records: deque[PacketRecord]  # jitter_ms 포함된 패킷 기록
self._last_by_code: Dict[int, Dict]  # msg_code별 마지막 timestamp/interval
```

---

### 📊 현재 결과
- **P95 ~ 0ms** (네트워크가 매우 안정적)

---

## 8. 수정 전/후 비교

### 오늘 수정한 내용 요약

| KPI | 수정 전 문제 | 수정 후 개선 |
|-----|-------------|-------------|
| **Timestamp** | UI 폴링 시점 사용 → 모든 패킷 같은 시간 | 캡처 시점 저장 → 정확한 시간 |
| **지터** | "간격" 자체를 지터로 계산 → 1000ms | "간격 변동"으로 계산 → ~0ms |
| **가용성** | 패킷 수 기반 → 0.3%에서 멈춤 | 연결 상태 기반 → ~100% |

---

### 변경된 파일

| 파일 | 변경 내용 |
|------|----------|
| `sniffer.py` | `capture_time = datetime.now()` 추가 |
| `queue.py` | 튜플 `(datetime, bytes)` 처리 |
| `live_provider.py` | `capture_time` 사용, msg_code 전달 |
| `packet_store.py` | 지터 간격 변동 기반, 가용성 연결 상태 기반, msg_code별 분리 |

---

## 📝 발표 포인트 정리

1. **두 가지 timestamp**: ICD 헤더 (송신측) vs 캡처 (수신측) 구분
2. **지터 = 간격의 변동**: 단순 간격이 아니라 변화량
3. **가용성 = 연결 상태**: 패킷 개수가 아니라 규칙성
4. **msg_code별 분리**: 0x01, 0x25, 0x40 각각 따로 계산

---

*멘토님께 확인 필요:*
- ICD 헤더 timestamp의 정확한 의미 (틱? ms? 카운터?)
- 시퀀스 번호 활성화 여부 (패킷 손실 계산용)
