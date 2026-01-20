# UGV-MON: VIC↔OCS Real-time Communication Monitoring Dashboard

A passive monitoring solution for VIC↔OCS UDP traffic, decoding ICD v1.0 messages and presenting operational status through an enterprise-grade Python Dash dashboard.

> **⚠️ Important**: This is NOT a control system. It performs passive monitoring only and must NEVER transmit control packets to the devices.

## 🎯 Project Purpose

UGV-MON provides real-time visibility into VIC (Vehicle Interface Controller) and OCS (Operator Control Station) communication quality and operational state for autonomous ground vehicle systems.

### Key Capabilities

- **Real-time Packet Capture**: Monitor UDP traffic on loopback (lo) or production interfaces (eno2/eno3)
- **ICD v1.0 Decoding**: Parse message headers, operational state, device connectivity, and emergency indicators
- **Quality Metrics**: Track availability, jitter (P95/P99), packet loss, and parse success rates
- **Enterprise Dashboard**: Professional monitoring UI with live charts and event logs

## 📁 Project Structure

```
opus1/
├── ugv_mon/                    # Main Python package
│   ├── app.py                  # Dash application factory
│   ├── config.py               # Configuration management
│   ├── capture/                # 패킷 캡처 모듈
│   │   ├── sniffer.py          # Scapy 기반 PacketSniffer
│   │   ├── queue.py            # 스레드 안전 PacketQueue
│   │   └── stats.py            # 캡처 통계 CaptureStats
│   ├── parser/                 # ICD 파싱 모듈
│   │   ├── models.py           # ICDHeader, StatusPayload, ParseResult
│   │   └── icd_parser.py       # 메인 파서 클래스
│   ├── analysis/               # 통계 분석 모듈
│   │   ├── stats_calculator.py # 지터, PPS, 가용성 계산
│   │   └── anomaly_detector.py # 이상 탐지
│   ├── data/                   # 데이터 모델 및 제공자
│   │   ├── models.py           # 타입 정의 (Enum, dataclass)
│   │   ├── mock_data.py        # Mock 데이터 생성기
│   │   └── live_provider.py    # 실시간 데이터 제공자
│   ├── components/             # UI 컴포넌트
│   ├── layouts/                # 레이아웃
│   ├── callbacks/              # Dash 콜백
│   └── utils/                  # 유틸리티
├── run.py                      # Entry point
├── start.sh                    # 실행 스크립트 (Mock/Live 전환)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10.12 or later (Linux에서는 `python3` 명령 사용)
- pip (Python package manager)

### Installation

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

---

## 🔄 실행 모드 (Mock / Live)

### 간편 실행 스크립트 사용

```bash
# Mock 모드 (가짜 데이터)
./start.sh mock

# Live 모드 - 루프백 (lo)
./start.sh live

# Live 모드 - 물리 인터페이스
./start.sh eno2
./start.sh eno3
```

### 직접 실행

#### 1. Mock 모드 (기본값, UI 테스트용)

```bash
python3 run.py
```

- **데이터 소스**: MockDataGenerator (랜덤 가짜 데이터)
- **권한**: 불필요
- **용도**: UI 개발/테스트

#### 2. Live 모드 - Local (lo 인터페이스)

```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 run.py
```

- **데이터 소스**: 실제 네트워크 패킷
- **권한**: root 필요
- **용도**: VIC↔OCS 시뮬레이터 테스트

#### 3. Live 모드 - 실장비 (eno2 또는 eno3)

```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=eno2    # 또는 eno3
sudo -E python3 run.py
```

- **데이터 소스**: 실제 VIC↔OCS 패킷
- **권한**: root 필요
- **용도**: 실제 장비 모니터링

### 권한 설정 (sudo 없이 실행)

```bash
# 한 번만 설정
sudo setcap cap_net_raw+ep $(which python3)

# 이후 sudo 없이 실행 가능
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
python3 run.py
```

---

## 환경변수 요약

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `UGV_MON_USE_LIVE` | `true`면 Live 모드 | (Mock 모드) |
| `UGV_MON_INTERFACE` | 캡처 인터페이스 | `lo` |
| `UGV_MON_PORT` | 서버 포트 | `8050` |
| `UGV_MON_POLL_INTERVAL` | 폴링 간격 (ms) | `2000` |
| `UGV_MON_DEBUG` | 디버그 모드 | `true` |

---

## 🖥️ Dashboard Overview

### Header Bar
- **Connection Status**: Shows if packets are being received
- **Interface**: Active network interface (lo, eno2, eno3)
- **Filter**: Active UDP port filter (50000→61000)
- **Last Packet Time**: Timestamp of most recent packet

### KPI Cards (8 metrics)
| Metric | Description |
|--------|-------------|
| 수신 pps | Packets per second captured |
| 필터 통과율 | % of packets matching VIC→OCS filter |
| 파싱 성공률 | % of packets successfully parsed |
| 체크섬 오류율 | % of checksum verification failures |
| 추정 패킷 손실 | Estimated lost packets from seq gaps |
| 가용성 (5분) | 5-minute rolling availability % |
| 가용성 (1시간) | 1-hour rolling availability % |
| 지터 (P95/P99) | Jitter percentiles in milliseconds |

### Status Panels
- **운용 상태**: Current operation mode, authority, and driving state
- **비상정지/이상 원인**: 10 emergency stop cause indicators
- **장치 연결 상태**: 10-device connectivity grid (VIC, RDC, ADC, etc.)

### Charts
- **통신 품질 차트**: PPS and jitter time series with P95/P99 reference lines
  - 시간 범위 선택 (30초, 1분, 5분)
  - 범례 표시 (PPS 좌, 지터 우)
  - 하단 실시간 값 표시 (PPS, 지터)
- **가용성 타임라인**: Up/down segments over 1-hour window

### Log Table
- Real-time packet log with sequence numbers, parse status, and anomaly notes
- Time 포맷: HH:MM:SS
- Controls: Pause, Clear

---

## 📋 ICD v1.0 Parsing Overview

### Message Structure

| Field | Size | Description |
|-------|------|-------------|
| TimeStamp | 4 bytes | Last byte is sequence number |
| MSG ID | 4 bytes | Source ID, Dest ID, Code, Ack |
| Reserved | 2 bytes | Reserved field |
| DataLength | 2 bytes | Payload size |
| Data | Variable | Up to 1010 bytes |
| Checksum | 2 bytes | Sum of all bytes & 0xFFFF |

### Key Payload Fields (Status Report, Code 0x01)

1. **Device Presence** (uint16, bits 9..0):
   - Bit 9: TM, Bit 8: TCC, Bit 7: DIP, Bit 6: SCS
   - Bit 5: ACAM, Bit 4: RCAM, Bit 3: FCAM
   - Bit 2: ADC, Bit 1: RDC, Bit 0: VIC

2. **VIC State Byte** (uint8):
   - Bits 7..5: Operation mode (prep/transition/unmanned driving/firing/emergency)
   - Bits 3..2: Authority (released/OCS/near controller)
   - Bits 1..0: Driving state (remote/platooning/autonomous)

3. **Emergency Sources** (uint16, bits 15..6):
   - 10 possible emergency stop causes

---

## 🧪 Testing

### 모듈별 테스트

#### 1. Capture 모듈 테스트
```bash
sudo python3 -c "
from ugv_mon.capture import PacketSniffer
import time

def callback(data):
    print(f'Received: {len(data)} bytes')

sniffer = PacketSniffer('lo', 50000, 61000, callback)
sniffer.start()
time.sleep(10)
sniffer.stop()
print(f'Total: {sniffer.get_stats().packets_total}')
"
```

#### 2. ICD 파싱 통합 테스트
```bash
sudo python3 test_icd_parsing.py
```

#### 3. Live 모드 통합 테스트
```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 test_live_mode.py
```

### 전체 대시보드 테스트

```bash
# Terminal 1: Start VCS Simulator
sudo ./VCS_Simulator -L

# Terminal 2: Start VCS Application
sudo ./VCS_Application

# Terminal 3: Run Dashboard (Live mode)
./start.sh live
```

### Wireshark Verification
- Interface: `lo` (loopback)
- Filter: `udp.srcport == 50000 && udp.dstport == 61000`
- Expected: 143-byte packets (101 bytes application data)

### 테스트 가이드
자세한 테스트 방법은 [`docs/TESTING_GUIDE.md`](docs/TESTING_GUIDE.md)를 참고하세요.

---

## 📅 Development Timeline

| Day | Focus | Status |
|-----|-------|--------|
| 1 | UI Skeleton | ✅ 완료 |
| 2 | Scapy Capture | ✅ 완료 |
| 3 | ICD Parsing | ✅ 완료 |
| 4 | Live Provider | ✅ 완료 |
| 5 | Stats Analysis | ✅ 완료 |
| 6 | UI Integration | ✅ 완료 |
| 7 | Stabilization | 문서 완료 |
| 8 | Charts | ✅ 완료 |
| 9 | Polish | ✅ 완료 |
| 10 | Hardening | 문서 완료 |

---

## 📄 License

Internal use only - Hanwha Aerospace Autonomous SW Team

## 🙏 Acknowledgments

- Dash/Plotly team for the excellent Python dashboard framework
- Dash Mantine Components for enterprise-grade UI components
- AG-Grid for high-performance data tables
