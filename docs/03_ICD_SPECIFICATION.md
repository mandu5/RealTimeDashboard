# ICD v1.0 파싱 규격 상세

---

## 메시지 구조

### 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    ICD v1.0 메시지 구조                      │
├──────────┬──────────┬──────────┬────────────┬───────┬───────┤
│TimeStamp │  MSG ID  │ Reserved │ DataLength │ Data  │Chksum │
│ (4 bytes)│ (4 bytes)│ (2 bytes)│ (2 bytes)  │(가변) │(2 B)  │
├──────────┼──────────┼──────────┼────────────┼───────┼───────┤
│ 0-3      │ 4-7      │ 8-9      │ 10-11      │ 12-N  │ N+1-2 │
└──────────┴──────────┴──────────┴────────────┴───────┴───────┘
```

**총 길이**: `12 (헤더) + DataLength + 2 (체크섬)` bytes

---

## 헤더 필드 상세

### 1. TimeStamp (4 bytes, Little Endian)

```
┌─────────┬─────────┬─────────┬─────────────────────────────┤
│ Byte 0  │ Byte 1  │ Byte 2  │ Byte 3 (Sequence Number)    │
└─────────┴─────────┴─────────┴─────────────────────────────┘
                                      │
                                      ▼
                              0~255 순환 (rollover)
                              손실 추정에 사용
```

**파싱 방법**:
```python
timestamp = struct.unpack('<I', data[0:4])[0]  # 4-byte unsigned int
sequence = data[3]  # 마지막 1 byte만 시퀀스 번호
```

**시퀀스 번호 활용**:
- 패킷 고유 번호로 사용
- `prev_seq`와 `curr_seq` 차이가 1이 아니면 누락 추정
- 8비트이므로 0~255 순환 처리 필요

---

### 2. MSG ID (4 bytes)

```
┌───────────┬───────────┬───────────┬───────────────────────┤
│ Source ID │ Dest ID   │ Code      │ Ack Flag              │
│ (1 byte)  │ (1 byte)  │ (1 byte)  │ (1 byte)              │
└───────────┴───────────┴───────────┴───────────────────────┘
```

**파싱 방법**:
```python
source_id = data[4]
dest_id = data[5]
msg_code = data[6]
ack_flag = data[7]
```

**상태보고 예시**: `0xB1A201FF`
- Source ID: `0xB1`
- Dest ID: `0xA2`
- Code: `0x01` (상태보고)
- Ack Flag: `0xFF`

---

### 3. Reserved (2 bytes)

- 현재 사용되지 않음
- 파싱은 필요하나 상태 추출에는 불필요

**파싱 방법**:
```python
reserved = struct.unpack('<H', data[8:10])[0]  # 2-byte unsigned short
```

---

### 4. DataLength (2 bytes, Little Endian)

**파싱 방법**:
```python
data_length = struct.unpack('<H', data[10:12])[0]  # 2-byte unsigned short
```

**상태보고**: DataLength = `87` (0x0057)

---

## 페이로드 필드 (상태보고, Code 0x01)

### 1. 구성품 연결 여부 (uint16, 2 bytes, Little Endian)

```
┌─────────────────────────────────────────────────────────────┐
│ Bit │ 9   │ 8   │ 7   │ 6   │ 5   │ 4    │ 3    │ 2   │ 1   │ 0   │
│ 장치│ TM  │ TCC │ DIP │ SCS │ AUX │ RCAM │ FCAM │ ADC │ RDC │ VIC │
│ 1=연결, 0=미연결                                            │
└─────────────────────────────────────────────────────────────┘
```

**파싱 방법**:
```python
device_presence = struct.unpack('<H', payload[0:2])[0]

# 비트별 확인
devices_connected = []
device_names = ["VIC", "RDC", "ADC", "FCAM", "RCAM", "AUX", "SCS", "DIP", "TCC", "TM"]
for i, name in enumerate(device_names):
    connected = bool(device_presence & (1 << i))
    devices_connected.append({"name": name, "connected": connected})
```

---

### 2. VIC 운용 상태 (uint8, 1 byte)

```
┌─────────────────────────────────────────────────────────────┐
│ Bit 7-5: 운용모드                                           │
│   000: 운용준비 (PREP)                                      │
│   001: 유무인전환 (TRANSITION)                              │
│   010: 무인주행 (UNMANNED DRIVING)                          │
│   011: 무인사격 (UNMANNED FIRING)                           │
│   100: 비상정지 (EMERGENCY STOP)                            │
├─────────────────────────────────────────────────────────────┤
│ Bit 3-2: 운용권한                                           │
│   00: 반납 (RELEASED)                                       │
│   01: OCS 획득 (OCS ACQUIRED)                               │
│   10: 근거리조종기 획득 (NEAR CONTROLLER)                   │
├─────────────────────────────────────────────────────────────┤
│ Bit 1-0: 주행상태                                           │
│   01: 원격주행 (REMOTE)                                     │
│   10: 종속주행 (PLATOON)                                    │
│   11: 자율배치 (AUTONOMOUS DISPATCH)                        │
└─────────────────────────────────────────────────────────────┘
```

**파싱 방법**:
```python
vic_state = payload[2]

# 비트 추출
operation_mode = (vic_state >> 5) & 0x07      # bits 7-5
authority = (vic_state >> 2) & 0x03            # bits 3-2
driving_state = vic_state & 0x03               # bits 1-0
```

**변환 예시**:
```python
# 운용모드 변환
mode_labels = {
    0b000: "준비 (PREP)",
    0b001: "전환 중 (TRANSITION)",
    0b010: "무인 주행 (UNMANNED DRIVING)",
    0b011: "무인 사격 (UNMANNED FIRING)",
    0b100: "비상 정지 (EMERGENCY STOP)",
}
mode_label = mode_labels.get(operation_mode, f"알 수 없음 ({operation_mode})")

# 권한 변환
authority_labels = {
    0b00: "해제됨 (RELEASED)",
    0b01: "OCS 획득 (OCS ACQUIRED)",
    0b10: "근거리조종기 (NEAR CONTROLLER)",
}
authority_label = authority_labels.get(authority, f"알 수 없음 ({authority})")

# 주행상태 변환
driving_labels = {
    0b01: "원격 (REMOTE)",
    0b10: "군집 (PLATOON)",
    0b11: "자율 파견 (AUTONOMOUS DISPATCH)",
}
driving_label = driving_labels.get(driving_state, f"알 수 없음 ({driving_state})")
```

---

### 3. 비상정지 원인 (uint16, 2 bytes, bits 15-6)

```
┌─────────────────────────────────────────────────────────────┐
│ Bit 15: 수동정지(근거리조종기)                              │
│ Bit 14: 수동정지(운용통제장치)                              │
│ Bit 13: 신호단절(통신)                                      │
│ Bit 12: 신호단절(동력계)                                    │
│ Bit 11: 신호단절(항법)                                      │
│ Bit 10: 신호단절(자율)                                      │
│ Bit 9:  신호단절(주행)                                      │
│ Bit 8:  장비고장(동력계)                                    │
│ Bit 7:  장비고장(주행)                                      │
│ Bit 6:  통신두절                                            │
└─────────────────────────────────────────────────────────────┘
```

**파싱 방법**:
```python
emergency_word = struct.unpack('<H', payload[3:5])[0]
emergency_bits = (emergency_word >> 6) & 0x3FF  # bits 15-6

# 비트별 확인
emergency_names = [
    "통신 두절",           # bit 6
    "장비고장(주행)",      # bit 7
    "장비고장(동력계)",    # bit 8
    "신호단절(주행)",      # bit 9
    "신호단절(자율)",      # bit 10
    "신호단절(항법)",      # bit 11
    "신호단절(동력계)",    # bit 12
    "신호단절(통신)",      # bit 13
    "수동정지(운용통제장치)",  # bit 14
    "수동정지(근거리조종기)",  # bit 15
]

emergency_status = {}
for i, name in enumerate(emergency_names):
    emergency_status[name] = bool(emergency_bits & (1 << i))
```

---

## 체크섬 검증

### 체크섬 규칙

> **체크섬 = (체크섬 필드 제외 모든 바이트 합) & 0xFFFF**

### 구현 코드

```python
def calculate_checksum(data: bytes) -> int:
    """
    체크섬 계산
    
    Args:
        data: 체크섬 필드를 제외한 모든 바이트
        
    Returns:
        계산된 체크섬 값 (2 bytes, Little Endian)
    """
    return sum(data) & 0xFFFF


def verify_checksum(packet: bytes) -> bool:
    """
    패킷 무결성 검증
    
    Args:
        packet: 전체 ICD 메시지 (체크섬 포함)
        
    Returns:
        True if checksum matches, False otherwise
    """
    if len(packet) < 2:
        return False
    
    # 체크섬 필드 제외
    data_without_checksum = packet[:-2]
    
    # 수신된 체크섬 추출
    received_checksum = struct.unpack('<H', packet[-2:])[0]
    
    # 계산된 체크섬
    calculated_checksum = calculate_checksum(data_without_checksum)
    
    return calculated_checksum == received_checksum
```

### 체크섬 검증 예시

```python
# 예시: 전체 패킷 길이가 101 bytes인 경우
# - 헤더: 12 bytes
# - 데이터: 87 bytes (DataLength = 87)
# - 체크섬: 2 bytes
# 총: 101 bytes

packet = b'...'  # 101 bytes
is_valid = verify_checksum(packet)
```

---

## 전체 파싱 플로우

### 파싱 순서

```
1. 최소 길이 검증
   └─ len(packet) >= 14 (헤더 12 + 체크섬 2)

2. 체크섬 검증
   └─ verify_checksum(packet)

3. 헤더 파싱
   ├─ TimeStamp (4 bytes)
   ├─ MSG ID (4 bytes)
   ├─ Reserved (2 bytes)
   └─ DataLength (2 bytes)

4. 길이 검증
   └─ len(packet) == 12 + DataLength + 2

5. 페이로드 파싱 (Code 0x01인 경우)
   ├─ 구성품 연결 여부 (2 bytes)
   ├─ VIC 운용 상태 (1 byte)
   └─ 비상정지 원인 (2 bytes)

6. 결과 반환
   └─ ParseResult(success, header, payload, checksum_ok, error)
```

### 파싱 실패 처리

| 경우 | 처리 방법 |
|------|----------|
| 패킷 너무 짧음 | `success=False`, `error="Packet too short"` |
| 체크섬 불일치 | `success=False`, `checksum_ok=False` |
| 길이 불일치 | `success=False`, `error="Length mismatch"` |
| Unknown 메시지 코드 | `payload=None`, `success=True` (헤더는 파싱됨) |

---

## Python struct 포맷 참고

| 타입 | 포맷 문자 | 바이트 수 |
|------|----------|----------|
| unsigned char | `B` | 1 |
| unsigned short (Little Endian) | `<H` | 2 |
| unsigned int (Little Endian) | `<I` | 4 |

### 예시

```python
import struct

# 1 byte
byte_value = data[0]  # 또는 struct.unpack('B', data[0:1])[0]

# 2 bytes Little Endian
short_value = struct.unpack('<H', data[0:2])[0]

# 4 bytes Little Endian
int_value = struct.unpack('<I', data[0:4])[0]
```

---

## 시퀀스 번호 롤오버 처리

### 문제

시퀀스 번호는 8비트 (0~255)이므로 255 다음에는 0으로 순환합니다.

### 롤오버 감지

```python
def seq_gap_with_rollover(prev_seq: int, curr_seq: int, max_seq: int = 256) -> int:
    """
    롤오버를 고려한 시퀀스 갭 계산
    
    Args:
        prev_seq: 이전 시퀀스 번호 (0-255)
        curr_seq: 현재 시퀀스 번호 (0-255)
        max_seq: 최대 시퀀스 값 (256)
        
    Returns:
        갭 값 (정상: 1, 손실: >1)
    """
    if curr_seq >= prev_seq:
        # 정상 순차 진행 또는 롤오버 후 첫 패킷
        return curr_seq - prev_seq
    else:
        # 롤오버 발생 (예: 255 -> 0)
        return (max_seq - prev_seq) + curr_seq
```

### 예시

```python
# 정상: 10 -> 11
gap = seq_gap_with_rollover(10, 11)  # 1

# 손실: 10 -> 15
gap = seq_gap_with_rollover(10, 15)  # 5 (4개 패킷 손실)

# 롤오버: 255 -> 0
gap = seq_gap_with_rollover(255, 0)  # 1 (정상)

# 롤오버 + 손실: 254 -> 2
gap = seq_gap_with_rollover(254, 2)  # 4 (3개 패킷 손실)
```

---

## 참고사항

1. **Endianness**: 모든 다중 바이트 필드는 **Little Endian**
2. **비트 순서**: 비트 0이 LSB (Least Significant Bit)
3. **체크섬 검증**: 반드시 체크섬 검증 후 상태 추출
4. **Unknown 패킷**: 길이나 체크섬이 올바르면 헤더는 파싱 가능
