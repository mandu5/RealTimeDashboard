# Testing Checklist

## Prerequisites

1. **Simulator Running:**
   ```bash
   sudo ./VCS_Simulator -L
   sudo ./VCS_Application
   ```

2. **Dashboard Running:**
   ```bash
   python3 run.py
   ```

3. **Wireshark Open (Optional):**
   - Interface: `lo`
   - Filter: `udp.srcport == 50000 && udp.dstport == 61000`

## Day 1 Tests: UI Skeleton

### Layout Rendering

- [ ] Dashboard loads without errors
- [ ] Header bar displays title "VIC↔OCS 실시간 모니터링"
- [ ] All 8 KPI cards render
- [ ] Device grid shows 10 devices
- [ ] Communication chart renders (PPS + Jitter)
- [ ] Availability timeline renders
- [ ] Log table (AG-Grid) renders with columns

### Status Indicators

- [ ] Status chips display: 연결상태, 인터페이스, 필터, 마지막 패킷
- [ ] Operational status shows: 운용모드, 운용권한, 주행상태
- [ ] Emergency status shows 10 indicators

### Polling/Updates

- [ ] Data updates every 2 seconds (check chart movement)
- [ ] KPI values change periodically
- [ ] Log entries appear in table
- [ ] Charts update smoothly

### Control Buttons

- [ ] Pause button stops updates
- [ ] Resume button restarts updates
- [ ] Clear button clears log entries
- [ ] Auto-scroll button toggles (visual feedback)

## Day 2 Tests: Scapy Capture

### Basic Capture

- [ ] Capture starts without permission errors
- [ ] Packets captured on loopback interface
- [ ] Filter correctly selects 50000→61000 traffic
- [ ] Capture PPS matches Wireshark count

### Filter Verification

- [ ] Only VIC→OCS packets pass filter
- [ ] Other UDP traffic rejected
- [ ] Filter pass percentage calculated correctly

## Day 3 Tests: ICD Parsing

### Header Parsing

- [ ] Timestamp extracted (4 bytes, little-endian)
- [ ] MSG ID extracted (Source, Dest, Code, Ack)
- [ ] Data length extracted correctly
- [ ] Checksum extracted and verified

### Payload Parsing

- [ ] Device bits decoded (all 10 devices)
- [ ] VIC state byte decoded (mode, authority, driving)
- [ ] Emergency bits decoded (10 causes)

### Simulator Correlation

- [ ] Device toggle in simulator → Grid updates
- [ ] Mode change in simulator → Mode display updates
- [ ] Emergency trigger → Indicator turns red

## Day 4 Tests: Quality Metrics

### Parse Success Rate

- [ ] Valid packets: parse_ok = True
- [ ] Invalid packets: parse_ok = False with reason
- [ ] Success percentage calculated correctly

### Checksum Verification

- [ ] Valid packets: checksum_ok = True
- [ ] Corrupted packets: checksum_ok = False
- [ ] Failure percentage calculated correctly

### Log Entries

- [ ] All packets logged with timestamp
- [ ] Sequence number recorded
- [ ] Anomalies noted in "Notes" column

## Day 5 Tests: Availability

### Down Detection

- [ ] Stop simulator → Connection indicator changes
- [ ] Availability percentage decreases
- [ ] Timeline shows red segment

### Recovery Detection

- [ ] Restart simulator → Connection restores
- [ ] New green segment appears on timeline
- [ ] Availability recalculates

### Time Windows

- [ ] 5-minute availability correct after 5+ minutes
- [ ] 1-hour availability correct after 60+ minutes
- [ ] Segment pruning keeps timeline bounded

## Day 6 Tests: Jitter & Loss

### Jitter Calculation

- [ ] P95 value reasonable (< jitter threshold)
- [ ] P99 value >= P95
- [ ] Reference lines on chart match KPI values

### Loss Estimation

- [ ] Consecutive packets: loss = 0
- [ ] Sequence gap: loss increments
- [ ] Rollover handled (255 → 0 not counted as loss)

## Day 7-9 Tests: Integration

### End-to-End Flow

- [ ] Simulator packet → Capture → Parse → UI
- [ ] All panels update from live data
- [ ] No data store corruption over time

### Long-Running Stability

- [ ] 30-minute run: No memory growth
- [ ] Log buffer stays bounded (< 200 entries)
- [ ] Chart buffer stays bounded (60 points)

## Day 10 Tests: Demo Preparation

### Demo Script

1. Start simulator and dashboard
2. Point out: Header shows "연결됨"
3. Highlight: KPI cards updating
4. Show: Device grid (9/10 connected)
5. Toggle simulator device → Watch grid update
6. Trigger emergency → Watch indicator
7. Stop simulator → Show availability drop
8. Resume simulator → Show recovery
9. Show log table with packet history
10. Pause/Resume/Clear buttons demo

### Error Scenarios

- [ ] Simulator not running → "연결끊김" shown
- [ ] Invalid packet → Logged with parse_ok = ✗
- [ ] Checksum failure → Logged with checksum_ok = ✗
