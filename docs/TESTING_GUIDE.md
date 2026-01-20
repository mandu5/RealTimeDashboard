# UGV-MON 테스트 가이드

> **작성일**: 2026-01-20  
> **목적**: 각 모듈별 테스트 방법 및 통합 테스트 가이드

---

## 📋 목차

1. [모듈별 단위 테스트](#모듈별-단위-테스트)
2. [통합 테스트](#통합-테스트)
3. [Live 모드 테스트](#live-모드-테스트)
4. [문제 해결](#문제-해결)

---

## 🔧 모듈별 단위 테스트

### 1. Capture 모듈 테스트

#### 기본 캡처 테스트

```bash
sudo python3 -c "
from ugv_mon.capture import PacketSniffer, PacketQueue
import time

queue = PacketQueue()

def callback(data):
    print(f'Received: {len(data)} bytes')

sniffer = PacketSniffer(
    interface='lo',
    src_port=50000,
    dst_port=61000,
    callback=callback
)

sniffer.start()
print('Sniffer running... (Ctrl+C to stop)')

try:
    time.sleep(10)  # 10초간 캡처
except KeyboardInterrupt:
    pass

sniffer.stop()
stats = sniffer.get_stats()
print(f'Total packets: {stats.packets_total}')
print(f'PPS: {stats.get_pps()}')
"
```

**예상 결과**:
- 패킷이 수신되면 "Received: XXX bytes" 메시지 출력
- 통계에 패킷 수 및 PPS 표시

---

### 2. Parser 모듈 테스트

#### ICD 파싱 테스트

```bash
python3 -c "
from ugv_mon.parser import ICDParser
import struct

# 테스트 패킷 생성
timestamp = 12345678
sequence = 42
source_id = 0xB1
dest_id = 0xA2
msg_code = 0x01
ack_flag = 0xFF
reserved = 0
data_length = 5

header = struct.pack('<I', timestamp)
header += bytes([source_id, dest_id, msg_code, ack_flag])
header += struct.pack('<H', reserved)
header += struct.pack('<H', data_length)

# 페이로드
device_presence = 0x03FF
vic_state = 0b01001001
emergency = 0x0000

payload = struct.pack('<H', device_presence)
payload += bytes([vic_state])
payload += struct.pack('<H', emergency)

# 체크섬
data_without_checksum = header + payload
checksum = sum(data_without_checksum) & 0xFFFF
packet = data_without_checksum + struct.pack('<H', checksum)

# 파싱
parser = ICDParser()
result = parser.parse(packet)

print(f'Parse success: {result.success}')
print(f'Checksum OK: {result.checksum_ok}')
if result.header:
    print(f'Sequence: {result.header.sequence}')
    print(f'MSG Code: 0x{result.header.msg_code:02X}')
if result.payload:
    print(f'Operation Mode: {result.payload.operation_mode_label}')
    print(f'Authority: {result.payload.authority_label}')
    print(f'Driving State: {result.payload.driving_state_label}')
"
```

**예상 결과**:
- `Parse success: True`
- `Checksum OK: True`
- 운용 모드, 권한, 주행 상태 출력

---

### 3. Analysis 모듈 테스트

#### 통계 계산 테스트

```bash
python3 -c "
from ugv_mon.analysis import StatsCalculator
from datetime import datetime, timedelta

calc = StatsCalculator(window_sec=60)

base_time = datetime.now()
for i in range(10):
    jitter = calc.record_packet(
        timestamp=base_time + timedelta(milliseconds=i*100),
        sequence=i,
        size=100
    )
    if jitter:
        print(f'Packet {i}: jitter={jitter:.2f}ms')

stats = calc.get_stats_dict()
print(f'PPS: {stats[\"pps\"]}')
print(f'Avg Jitter: {stats[\"jitter_avg\"]}ms')
print(f'P95 Jitter: {stats[\"jitter_p95\"]}ms')
print(f'P99 Jitter: {stats[\"jitter_p99\"]}ms')
"
```

**예상 결과**:
- 각 패킷의 지터 값 출력
- PPS, 평균 지터, P95/P99 백분위수 출력

---

## 🔗 통합 테스트

### 1. ICD 파싱 통합 테스트

**파일**: `test_icd_parsing.py`

**실행 방법**:
```bash
sudo python3 test_icd_parsing.py
```

**테스트 내용**:
- 패킷 캡처 + ICD 파싱 연동
- 파싱 성공/실패 통계
- 체크섬 검증 결과
- 운용 상태 파싱 확인

**예상 출력**:
```
============================================================
ICD 파싱 통합 테스트
============================================================

✅ Sniffer started on interface 'lo'
   Filter: UDP 50000→61000

✅ [1] Parse OK: Seq=42, Code=0x01, Size=101B
   Mode: 무인 주행 (UNMANNED DRIVING)
   Authority: 근거리조종기 (NEAR CONTROLLER)
   Driving: 원격 (REMOTE)
   Connected Devices: VIC, RDC, ADC, ...

============================================================
테스트 결과
============================================================
총 패킷 수: 10
파싱 성공: 10
체크섬 실패: 0
성공률: 100.0%
```

---

### 2. Live 모드 통합 테스트

**파일**: `test_live_mode.py`

**실행 방법**:
```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 test_live_mode.py
```

**테스트 내용**:
- LiveDataProvider 생성 및 캡처 시작
- 데이터 업데이트 루프 테스트
- 실시간 메트릭 확인

**예상 출력**:
```
============================================================
Live 모드 통합 테스트
============================================================

✅ Provider 생성: LiveDataProvider
✅ 캡처 시작 성공!

[ 1s] 🟢 PPS: 1024, Last: 14:32:05, Logs: 1
[ 2s] 🟢 PPS: 1024, Last: 14:32:07, Logs: 2
...

============================================================
최종 통계
============================================================
연결 상태: True
수신 PPS: 1024
파싱 성공률: 100.0%
체크섬 실패율: 0.0%
패킷 손실: 0
지터 P95: 2.1ms
지터 P99: 2.4ms
로그 개수: 10
```

---

## 🌐 Live 모드 테스트

### 전체 대시보드 실행 테스트

**실행 방법**:
```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 run.py
```

**확인 사항**:

1. **터미널 출력 확인**
   ```
   Mode: LIVE (실시간 캡처)
   Interface: lo
   [INFO] Using LiveDataProvider (real-time capture)
   [INFO] Sniffer started on interface 'lo'
   ```

2. **브라우저 접속** (`http://localhost:8050`)

3. **대시보드 확인**:
   - ✅ 헤더 바: "연결상태"가 "연결됨" (녹색)
   - ✅ KPI 카드: "수신 pps"가 0보다 큰 값
   - ✅ 로그 테이블: 실제 패킷 로그 표시
   - ✅ 차트: PPS 및 지터 그래프 업데이트
   - ✅ 장치 연결: 실제 장치 상태 표시

---

## 🐛 문제 해결

### 문제 1: 패킷이 캡처되지 않음

**증상**: PPS가 0, 로그 테이블이 비어있음

**확인 방법**:
```bash
# tcpdump로 패킷 확인
sudo tcpdump -i lo "udp and src port 50000 and dst port 61000"
```

**해결책**:
- VIC↔OCS 시뮬레이터/장비가 실행 중인지 확인
- 인터페이스가 올바른지 확인 (`ip link show`)
- BPF 필터 포트 확인 (50000→61000)

---

### 문제 2: 파싱 실패

**증상**: 파싱 성공률이 낮음, 로그에 "Parse FAILED" 메시지

**확인 방법**:
```bash
# 파싱 통계 확인
python3 -c "
from ugv_mon.parser import ICDParser
parser = ICDParser()
stats = parser.get_stats()
print(stats)
"
```

**해결책**:
- 패킷 형식이 ICD v1.0 규격과 일치하는지 확인
- 체크섬 계산 로직 확인
- 패킷 크기 확인 (최소 14 bytes)

---

### 문제 3: 체크섬 실패

**증상**: 체크섬 실패율이 높음

**원인**:
- 패킷 손상
- 체크섬 계산 로직 오류
- 엔디안 문제

**해결책**:
- Wireshark로 패킷 확인
- 체크섬 계산 로직 재검증
- Little Endian 확인

---

## 📊 테스트 체크리스트

### 모듈별 테스트

- [ ] Capture 모듈: 패킷 캡처 성공
- [ ] Parser 모듈: ICD 파싱 성공
- [ ] Analysis 모듈: 통계 계산 정확

### 통합 테스트

- [ ] ICD 파싱 통합: 캡처 + 파싱 연동
- [ ] Live 모드 통합: LiveDataProvider 동작
- [ ] 대시보드 실행: UI에 데이터 표시

### Live 모드 테스트

- [ ] Mock 모드: 가짜 데이터 표시
- [ ] Live 모드 (lo): 실제 패킷 캡처
- [ ] Live 모드 (eno2/eno3): 실장비 연동

---

## 📝 테스트 스크립트

프로젝트 루트에 다음 테스트 스크립트가 있습니다:

- `test_icd_parsing.py`: ICD 파싱 통합 테스트
- `test_live_mode.py`: Live 모드 통합 테스트

**사용법**:
```bash
# ICD 파싱 테스트
sudo python3 test_icd_parsing.py

# Live 모드 테스트
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 test_live_mode.py
```

---

## 📚 관련 문서

- [`EXECUTION_GUIDE.md`](EXECUTION_GUIDE.md): 실행 방법 상세 가이드
- [`05_DAY02.md`](05_DAY02.md): 패킷 캡처 구현 상세
- [`06_DAY03.md`](06_DAY03.md): ICD 파싱 구현 상세

---

**마지막 업데이트**: 2026-01-20
