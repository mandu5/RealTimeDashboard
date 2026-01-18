# Two-Week Development Plan

## Overview

**Project:** UGV-MON (VIC↔OCS Real-time Communication Monitoring)  
**Duration:** Week 3 Monday → Week 4 Friday (10 working days)  
**Goal:** Enterprise-grade monitoring dashboard with live packet capture and ICD parsing

## Daily Schedule

### Week 3 (Days 1-5)

#### Day 1 (Mon) - Migration Scaffolding + UI Skeleton ✅

**Deliverables:**
- [x] Clean Python Dash project structure
- [x] DMC-based dashboard layout
- [x] Header bar with status chips
- [x] KPI cards row (8 metrics)
- [x] Operational status panels
- [x] Device connectivity grid
- [x] Emergency indicators panel
- [x] Communication charts (PPS + Jitter)
- [x] Availability timeline
- [x] AG-Grid log table setup
- [x] Polling callbacks (dcc.Interval)

**Test:** App runs locally; layout renders

**Commit Message:**
```
feat(ui): bootstrap dash layout with DMC and log grid skeleton

- Create modular ugv_mon package structure
- Implement reusable UI components (StatusChip, KpiCard, DeviceGrid)
- Set up dash-ag-grid for log/event table
- Configure DMC-based dashboard layout
- Add mock data generator for UI development
- Implement polling callbacks with dcc.Interval
```

---

#### Day 2 (Tue) - Scapy Capture + Filtering

**Deliverables:**
- [ ] `ugv_mon/capture/` module structure
- [ ] Scapy sniffer with async callback
- [ ] BPF filter for 50000→61000
- [ ] Packet queue for processing
- [ ] Basic counters: capture PPS, filter pass %

**Test:** Compare captured count to Wireshark

**Commit Message:**
```
feat(capture): add scapy sniffer with VIC→OCS UDP filter and basic metrics
```

---

#### Day 3 (Wed) - ICD Parsing MVP

**Deliverables:**
- [ ] `ugv_mon/parser/` module structure
- [ ] Header parser (12 bytes, little-endian)
- [ ] Payload parser (device bits, state byte, emergency)
- [ ] Checksum verification
- [ ] Sequence extraction from timestamp

**Test:** Toggle simulator features, verify parsed fields change

**Commit Message:**
```
feat(parser): implement ICD v1.0 status parsing, checksum verify, seq extraction
```

---

#### Day 4 (Thu) - Data Quality Metrics

**Deliverables:**
- [ ] `ugv_mon/analysis/quality.py`
- [ ] Parse success rate tracking
- [ ] Checksum failure rate tracking
- [ ] Length mismatch detection
- [ ] Unknown packet type counting
- [ ] Structured log entry model

**Test:** Send invalid packets, verify flagged in logs

**Commit Message:**
```
feat(quality): add parse/quality KPIs and structured log entries
```

---

#### Day 5 (Fri) - Availability Analysis

**Deliverables:**
- [ ] `ugv_mon/analysis/availability.py`
- [ ] Down threshold configuration
- [ ] Down segment detection
- [ ] Rolling availability calculation (5m, 1hr)
- [ ] Timeline data model

**Test:** Stop simulator, verify down segment appears

**Commit Message:**
```
feat(analysis): compute availability and down segments for timeline
```

---

### Week 4 (Days 6-10)

#### Day 6 (Mon) - Jitter + Loss Estimate

**Deliverables:**
- [ ] `ugv_mon/analysis/jitter.py`
- [ ] Inter-arrival time calculation
- [ ] P95/P99 percentile computation
- [ ] Sequence gap loss estimation
- [ ] Rollover handling (256 wrap)

**Test:** Run for minutes, verify plausible jitter values

**Commit Message:**
```
feat(analysis): add jitter stats (p95/p99) and seq-gap loss estimate
```

---

#### Day 7 (Tue) - Wire Backend to UI

**Deliverables:**
- [ ] Replace mock data with live capture
- [ ] Connect KPIs to analysis modules
- [ ] Device grid from parsed data
- [ ] Emergency badges from parsed data
- [ ] Status panels from parsed data

**Test:** Simulator actions → UI changes

**Commit Message:**
```
feat(ui): connect polling callbacks to live state, devices, and emergency panels
```

---

#### Day 8 (Wed) - Charts Implementation

**Deliverables:**
- [ ] PPS time series with range selector
- [ ] Jitter time series with P95/P99 lines
- [ ] Availability timeline (up/down bars)
- [ ] Smooth chart updates under polling

**Test:** Charts update without flicker

**Commit Message:**
```
feat(charts): add pps/jitter/availability charts with basic interactivity
```

---

#### Day 9 (Thu) - Log Table + Polish

**Deliverables:**
- [ ] AG-Grid with live log data
- [ ] Bounded log buffer (200 entries)
- [ ] Anomaly highlighting
- [ ] UI spacing/typography polish
- [ ] Color semantics consistency

**Test:** 30-60 minute run, logs stay bounded

**Commit Message:**
```
feat(logs): finalize ag-grid log view and UI polish for monitoring workflow
```

---

#### Day 10 (Fri) - Integration Hardening

**Deliverables:**
- [ ] `run.py` with proper error handling
- [ ] Minimal unit tests (checksum, bit extraction, rollover)
- [ ] Demo script document
- [ ] README finalization
- [ ] Code cleanup and documentation

**Test:** End-to-end demo: simulator → capture → parse → analysis → UI

**Commit Message:**
```
chore: harden integration, add minimal tests, and finalize documentation/demo steps
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Scapy permission issues | Test with sudo early; document requirements |
| ICD parsing ambiguity | Verify against Wireshark hex dumps |
| Performance under load | Implement bounded buffers; profile if needed |
| DMC version issues | Pin versions in requirements.txt |

## Success Criteria

1. Dashboard renders all components correctly
2. Live packets captured and parsed
3. KPIs update in real-time
4. Availability/jitter calculations accurate
5. 30+ minute stability without memory issues
6. Demo-ready for mentor review
