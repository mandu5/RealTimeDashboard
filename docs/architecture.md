# UGV-MON Architecture Overview

## CSCI/CSC/CSU Structure

This document describes the simplified software architecture per mentor requirements.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CSCI: UGV-MON                                   │
│           VIC↔OCS Real-time Communication Monitoring                │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   CSC-001     │     │   CSC-002     │     │   CSC-003     │
│ Data          │     │ Data          │     │ Data          │
│ Acquisition   │     │ Processing/   │     │ Presentation  │
│ (데이터 수집) │     │ Analysis      │     │ (데이터 전시) │
└───────┬───────┘     │(데이터처리/분석)│     └───────┬───────┘
        │             └───────┬───────┘             │
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ CSU:          │     │ CSU:          │     │ CSU:          │
│ 실시간        │     │ ICD 파싱      │     │ 상태 전시     │
│ 데이터 수집   │     └───────────────┘     └───────────────┘
└───────────────┘     ┌───────────────┐     ┌───────────────┐
┌───────────────┐     │ CSU:          │     │ CSU:          │
│ CSU:          │     │ 데이터 품질   │     │ 로그/이벤트   │
│ 데이터        │     │ 분석          │     │ 전시          │
│ 필터링        │     └───────────────┘     └───────────────┘
└───────────────┘     ┌───────────────┐     ┌───────────────┐
                      │ CSU:          │     │ CSU:          │
                      │ 운용 데이터   │     │ 성능 지표     │
                      │ 분석          │     │ 전시          │
                      └───────────────┘     └───────────────┘
```

## Code Mapping

| CSC | CSU | Python Module |
|-----|-----|---------------|
| CSC-001 | 실시간 데이터 수집 | `ugv_mon/capture/` (Day 2) |
| CSC-001 | 데이터 필터링 | `ugv_mon/capture/filter.py` (Day 2) |
| CSC-002 | ICD 파싱 | `ugv_mon/parser/` (Day 3) |
| CSC-002 | 데이터 품질 분석 | `ugv_mon/analysis/quality.py` (Day 4) |
| CSC-002 | 운용 데이터 분석 | `ugv_mon/analysis/operational.py` (Day 5-6) |
| CSC-003 | 상태 전시 | `ugv_mon/layouts/panels.py` |
| CSC-003 | 로그/이벤트 전시 | `ugv_mon/components/log_table.py` |
| CSC-003 | 성능 지표 전시 | `ugv_mon/components/kpi_card.py`, `layouts/charts.py` |

## Data Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Network  │     │ Scapy    │     │ ICD      │     │ Dash     │
│ Interface│────▶│ Capture  │────▶│ Parser   │────▶│ Dashboard│
│ (lo/eno2)│     │ + Filter │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                │                │
     │                │                │                │
     ▼                ▼                ▼                ▼
   UDP           Filtered         Parsed          Visualized
 Packets         Packets          State            UI
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Capture | Scapy | Packet sniffing and filtering |
| Processing | Python 3.10 | ICD parsing, analysis |
| State | dcc.Store | In-memory state management |
| Polling | dcc.Interval | 2-second update cycle |
| UI | Dash + DMC | Dashboard framework |
| Charts | Plotly | Time series visualization |
| Tables | AG-Grid | High-performance log table |

## Design Decisions

### Why Polling Over Push?

1. **Simplicity**: `dcc.Interval` is built-in and well-documented
2. **Reliability**: No WebSocket connection issues
3. **Adequate Latency**: 2-second updates sufficient for monitoring
4. **Development Speed**: Faster implementation within timeline

### Why Scapy Over Raw Sockets?

1. **Reduced Risk**: Scapy handles low-level packet details
2. **Built-in Filtering**: BPF filter syntax support
3. **Cross-platform**: Works on both loopback and physical interfaces
4. **Debugging**: Easy packet inspection during development

### Why Single-Page Dashboard?

1. **Operational Focus**: All monitoring data visible at once
2. **No Navigation**: Operators shouldn't hunt for information
3. **Real-time Updates**: Entire view updates coherently
4. **Performance**: Single page load, incremental updates
