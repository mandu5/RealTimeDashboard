# Analysis Implementation Rationale

## Priority Order: Availability → Jitter → Loss Estimate

Based on mentor feedback, the following analysis priorities were established:

### 1. Availability (Priority: Highest)

**Why First:**
- Most critical operational metric for UGV systems
- Direct impact on mission readiness assessment
- Clear definition: system is either receiving packets or not
- Straightforward implementation with timestamp tracking

**Implementation:**
- Track last packet timestamp
- Compare against configurable threshold (default: 5 seconds)
- Calculate rolling availability for 5-minute and 1-hour windows
- Visualize up/down segments in timeline chart

**Data Model:**
```python
@dataclass
class AvailabilitySegment:
    start_sec: float    # Start time in seconds
    end_sec: float      # End time in seconds  
    is_up: bool         # True = receiving, False = down
```

### 2. Jitter (Priority: High)

**Why Second:**
- Indicates communication quality stability
- P95/P99 percentiles standard in network monitoring
- Useful for detecting intermittent issues
- Can be calculated from inter-arrival times

**Implementation:**
- Calculate delta between consecutive packet timestamps
- Maintain rolling window of deltas
- Compute P95 and P99 from sorted deltas
- Display as KPI cards and reference lines on chart

**Calculation:**
```python
def calculate_jitter_percentile(deltas: List[float], percentile: int) -> float:
    sorted_deltas = sorted(deltas)
    index = int(len(sorted_deltas) * percentile / 100)
    return sorted_deltas[min(index, len(sorted_deltas) - 1)]
```

### 3. Packet Loss Estimate (Priority: Medium)

**Why Third:**
- Requires sequence number extraction (depends on ICD parsing)
- Estimate only - cannot confirm packets never arrived
- Useful for detecting systematic issues

**Implementation:**
- Extract sequence number from timestamp field (last byte)
- Handle 8-bit rollover (0-255)
- Calculate gaps between consecutive sequences
- Sum gaps as estimated loss

**Rollover Handling:**
```python
def seq_gap_with_rollover(prev_seq: int, curr_seq: int) -> int:
    if curr_seq >= prev_seq:
        return curr_seq - prev_seq
    else:
        return (256 - prev_seq) + curr_seq
```

## Deprioritized Analysis

### FSM/State Transition Validation

**Status:** Deprioritized (requires mentor-provided allowed transition table)

**Rationale:**
- Cannot validate without authoritative state machine definition
- Risk of false positives without proper transition rules
- May be added in future if transition table is provided

### UI Latency Metric

**Status:** Not displayed to users

**Rationale:**
- Mentor feedback explicitly excluded this metric
- UI latency is internal implementation detail
- Not relevant to VIC↔OCS communication quality

## Future Extensions (Out of Scope)

### Offline Replay/PCAPNG Ingestion

**Status:** Not required for first delivery

**Rationale:**
- Focus on real-time monitoring first
- Replay adds complexity with minimal immediate value
- Keep extension hook if time permits

### Advanced ML Analysis

**Status:** Deferred until confirmed appropriate

**Rationale:**
- Requires continuous signals and/or labeled data
- Current data may not support ML approaches
- Focus on interpretable statistics first
