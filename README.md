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
/workspace/
├── ugv_mon/                    # Main Python package
│   ├── __init__.py
│   ├── app.py                  # Dash application factory
│   ├── config.py               # Configuration management
│   ├── components/             # Reusable UI components
│   │   ├── status_chip.py      # Status indicator chips
│   │   ├── kpi_card.py         # KPI metric cards
│   │   ├── device_grid.py      # Device connectivity grid
│   │   └── log_table.py        # AG-Grid event table
│   ├── layouts/                # Dashboard layouts
│   │   ├── main_layout.py      # Complete dashboard composition
│   │   ├── header.py           # Header bar component
│   │   ├── panels.py           # Status panels
│   │   └── charts.py           # Plotly charts
│   ├── callbacks/              # Dash callbacks
│   │   └── update_callbacks.py # Polling and UI updates
│   ├── data/                   # Data models
│   │   ├── models.py           # Type definitions
│   │   └── mock_data.py        # Mock data generator
│   └── utils/                  # Utilities
│       └── helpers.py          # Helper functions
├── run.py                      # Entry point
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10.12 or later
- pip (Python package manager)

### Installation

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Dashboard

```bash
python run.py
```

Open your browser to: **http://localhost:8050**

### Environment Configuration

```bash
# Custom port
UGV_MON_PORT=8080 python run.py

# Production mode (no debug)
UGV_MON_DEBUG=false python run.py

# Change network interface
UGV_MON_INTERFACE=eno2 python run.py

# Faster polling (1 second)
UGV_MON_POLL_INTERVAL=1000 python run.py
```

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
  - X축 시간 레이블 최적화
- **가용성 타임라인**: Up/down segments over 1-hour window
  - 세그먼트 전체 영역에서 hover 정보 표시
  - 마지막 세그먼트가 타임윈도우 끝까지 유지

### Status Panels
- **장치 연결 상태**: 10-device connectivity grid
  - 경고/오류 상태 시 hover tooltip으로 원인 표시 (HTML title 속성)
  - 모든 박스 크기 동일 유지

### Log Table
- Real-time packet log with sequence numbers, parse status, and anomaly notes
- Time 포맷: HH:MM:SS (밀리초 제거)
- Controls: Pause, Clear

## ⚙️ Architecture

### CSC Structure (Per Mentor Requirements)

```
CSCI: UGV-MON
├── CSC-001: Data Acquisition (데이터 수집)
│   ├── CSU: 실시간 데이터 수집
│   └── CSU: 데이터 필터링
├── CSC-002: Data Processing/Analysis (데이터 처리/분석)
│   ├── CSU: ICD 파싱
│   ├── CSU: 데이터 품질 분석
│   └── CSU: 운용 데이터 분석
└── CSC-003: Data Presentation (데이터 전시)
    ├── CSU: 상태 전시
    ├── CSU: 로그/이벤트 전시
    └── CSU: 성능 지표 전시
```

### Polling Approach (vs. SocketIO Push)

This dashboard uses **dcc.Interval** polling (2-second default) instead of SocketIO push for several reasons:

1. **Simplicity**: Polling is straightforward to implement and debug
2. **Reliability**: No WebSocket connection management complexity
3. **Sufficient for Use Case**: 2-second updates are adequate for monitoring
4. **Resource Efficiency**: Bounded update frequency prevents overload
5. **Development Speed**: Faster to implement within internship timeline

SocketIO push remains an option for future enhancement if sub-second latency is required.

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
   - Bit 5: AUX, Bit 4: RCAM, Bit 3: FCAM
   - Bit 2: ADC, Bit 1: RDC, Bit 0: VIC

2. **VIC State Byte** (uint8):
   - Bits 7..5: Operation mode (prep/transition/unmanned driving/firing/emergency)
   - Bits 3..2: Authority (released/OCS/near controller)
   - Bits 1..0: Driving state (remote/platoon/autonomous)

3. **Emergency Sources** (uint16, bits 15..6):
   - 10 possible emergency stop causes

## 🧪 Testing with Simulator

### Setup
```bash
# Terminal 1: Start VCS Simulator
sudo ./VCS_Simulator -L

# Terminal 2: Start VCS Application
sudo ./VCS_Application

# Terminal 3: Run Dashboard
python run.py
```

### Wireshark Verification
- Interface: `lo` (loopback)
- Filter: `udp.srcport == 50000 && udp.dstport == 61000`
- Expected: 143-byte packets (101 bytes application data)

### Test Scenarios
1. **Normal Operation**: Verify PPS ~1000, parse success 100%
2. **Stop Simulator**: Check availability drops, connection indicator changes
3. **Emergency State**: Toggle simulator buttons, verify emergency indicators

## 📅 Development Timeline

| Day | Focus | Deliverables |
|-----|-------|--------------|
| 1 | UI Skeleton | Dash layout with DMC, AG-Grid setup ✅ |
| 2 | Scapy Capture | Real-time packet capture module |
| 3 | ICD Parsing | Header/payload parsing, checksum verification |
| 4 | Quality Metrics | Parse success, checksum fail, log entries |
| 5 | Availability | Uptime calculation, timeline segments |
| 6 | Jitter/Loss | P95/P99 jitter, seq-gap loss estimate |
| 7 | UI Integration | Connect live data to all components |
| 8 | Charts | PPS, jitter, availability visualizations |
| 9 | Polish | AG-Grid finalization, UI refinement |
| 10 | Hardening | Integration tests, demo preparation |

## 📝 Suggested Commit Message (Day 1)

```
feat(ui): bootstrap dash layout with DMC and log grid skeleton

- Create modular ugv_mon package structure
- Implement reusable UI components (StatusChip, KpiCard, DeviceGrid)
- Set up dash-ag-grid for log/event table
- Configure DMC-based dashboard layout
- Add mock data generator for UI development
- Implement polling callbacks with dcc.Interval
```

## 📄 License

Internal use only - Hanwha Aerospace Autonomous SW Team

## 🙏 Acknowledgments

- Dash/Plotly team for the excellent Python dashboard framework
- Dash Mantine Components for enterprise-grade UI components
- AG-Grid for high-performance data tables
