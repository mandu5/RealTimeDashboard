# 부록

---

## 환경변수 목록

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `UGV_MON_DEBUG` | `true` | 디버그 모드 |
| `UGV_MON_HOST` | `0.0.0.0` | 서버 호스트 |
| `UGV_MON_PORT` | `8050` | 서버 포트 |
| `UGV_MON_INTERFACE` | `lo` | 캡처 인터페이스 |
| `UGV_MON_POLL_INTERVAL` | `2000` | 폴링 주기 (ms) |

### 사용 예시

```bash
# 포트 변경
UGV_MON_PORT=8080 python run.py

# 프로덕션 모드
UGV_MON_DEBUG=false python run.py

# 인터페이스 변경
UGV_MON_INTERFACE=eno2 sudo python run.py

# 폴링 주기 변경
UGV_MON_POLL_INTERVAL=1000 python run.py
```

---

## 주요 색상 코드

| 용도 | 색상 | Hex |
|------|------|-----|
| 성공/연결 | 초록 | `#10b981` |
| 경고 | 노랑 | `#f59e0b` |
| 오류/단절 | 빨강 | `#ef4444` |
| 기본 | 파랑 | `#3b82f6` |
| 배경 | 회색 | `#f8fafc` |

---

## ICD 비트 매핑 요약

### 장치 연결 (bits 9-0)

```python
DEVICES = {
    0: "VIC",
    1: "RDC",
    2: "ADC",
    3: "FCAM",
    4: "RCAM",
    5: "AUX",
    6: "SCS",
    7: "DIP",
    8: "TCC",
    9: "TM"
}
```

### 운용모드 (bits 7-5)

```python
MODES = {
    0b000: "준비 (PREP)",
    0b001: "전환 중 (TRANSITION)",
    0b010: "무인 주행 (UNMANNED DRIVING)",
    0b011: "무인 사격 (UNMANNED FIRING)",
    0b100: "비상 정지 (EMERGENCY STOP)"
}
```

### 권한 (bits 3-2)

```python
AUTH = {
    0b00: "해제됨 (RELEASED)",
    0b01: "OCS 획득 (OCS ACQUIRED)",
    0b10: "근거리조종기 (NEAR CONTROLLER)"
}
```

### 주행상태 (bits 1-0)

```python
DRIVE = {
    0b01: "원격 (REMOTE)",
    0b10: "군집 (PLATOON)",
    0b11: "자율 파견 (AUTONOMOUS DISPATCH)"
}
```

---

## 일별 커밋 메시지 요약

| Day | 커밋 메시지 |
|-----|------------|
| 1 | `feat(ui): bootstrap dash layout with DMC and log grid skeleton` |
| 2 | `feat(capture): add scapy sniffer with VIC→OCS UDP filter and basic metrics` |
| 3 | `feat(parser): implement ICD v1.0 status parsing, checksum verify, seq extraction` |
| 4 | `feat(quality): add parse/quality KPIs and structured log entries` |
| 5 | `feat(analysis): compute availability and down segments for timeline` |
| 6 | `feat(analysis): add jitter stats (p95/p99) and seq-gap loss estimate` |
| 7 | `feat(ui): connect polling callbacks to live state, devices, and emergency panels` |
| 8 | `feat(charts): add pps/jitter/availability charts with basic interactivity` |
| 9 | `feat(logs): finalize ag-grid log view and UI polish for monitoring workflow` |
| 10 | `chore: harden integration, add minimal tests, and finalize documentation/demo steps` |

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
byte_value = data[0]

# 2 bytes Little Endian
short_value = struct.unpack('<H', data[0:2])[0]

# 4 bytes Little Endian
int_value = struct.unpack('<I', data[0:4])[0]
```

---

## Scapy 권한 문제 해결

Scapy는 raw socket 접근이 필요하므로 root 권한이 필요합니다.

```bash
# 개발 환경
sudo python run.py

# 또는 sudo 없이 실행하려면
# (권장하지 않음 - 보안 위험)
sudo setcap cap_net_raw+eip $(which python3)
```

---

## 참고 자료

- [ICD v1.0 규격 문서](./03_ICD_SPECIFICATION.md)
- [아키텍처 문서](./01_ARCHITECTURE.md)
- [파일 구조 문서](./02_FILE_STRUCTURE.md)
- [개발 계획](./development_plan.md)
