"""
Data models for UGV-MON Dashboard.

Defines structured data types for:
- Dashboard state (KPIs, operational status)
- Log entries (packet records)
- Device status (connectivity grid)
- Availability segments (timeline)

These models ensure type safety and provide clear documentation
of the data structures used throughout the dashboard.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class OperationMode(Enum):
    """VIC operation mode (bits 7..5 of state byte)."""
    PREP = 0b000
    TRANSITION = 0b001
    UNMANNED_DRIVING = 0b010
    UNMANNED_FIRING = 0b011
    EMERGENCY_STOP = 0b100
    UNKNOWN = 0xFF


class Authority(Enum):
    # VIC authority state (bits 3..2 of state byte).
    RELEASED = 0b00
    OCS_ACQUIRED = 0b01
    NEAR_CONTROLLER = 0b10
    UNKNOWN = 0xFF


class DrivingState(Enum):
    """VIC driving state (bits 1..0 of state byte)."""
    REMOTE = 0b01
    PLATOON = 0b10
    AUTONOMOUS_DISPATCH = 0b11
    UNKNOWN = 0xFF


@dataclass
class DeviceStatus:
    """
    Status of a single device in the connectivity grid.
    
    Attributes:
        device_id: Unique identifier (vic, rdc, adc, etc.)
        name: Display name (VIC, RDC, ADC, etc.)
        connected: Whether device is reporting as connected
        warning: Whether device has a warning condition
        last_seen: Timestamp of last status update
    """
    device_id: str
    name: str
    connected: bool = True
    warning: bool = False
    last_seen: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for Dash component props."""
        return {
            "id": self.device_id,
            "name": self.name,
            "connected": self.connected,
            "warning": self.warning,
        }


@dataclass
class LogEntry:
    """
    Single log entry for the event table.
    
    Represents one parsed (or failed) packet with metadata.
    
    Attributes:
        timestamp: When packet was received
        sequence: Sequence number from ICD timestamp field
        msg_code: Message code from ICD header
        parse_ok: Whether ICD parsing succeeded
        checksum_ok: Whether checksum verification passed
        mode: Current operation mode (if parsed)
        authority: Current authority (if parsed)
        notes: Any anomaly notes (jitter, loss, etc.)
    """
    timestamp: datetime
    sequence: int
    msg_code: str
    parse_ok: bool = True
    checksum_ok: bool = True
    mode: str = ""
    authority: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for AG-Grid row data."""
        return {
            "time": self.timestamp.strftime("%H:%M:%S.%f")[:-3],  # HH:MM:SS.mmm
            "seq": self.sequence,
            "msg_code": self.msg_code,
            "parse_ok": "✓" if self.parse_ok else "✗",
            "checksum_ok": "✓" if self.checksum_ok else "✗",
            "mode": self.mode,
            "authority": self.authority,
            "notes": self.notes,
        }


@dataclass
class AvailabilitySegment:
    """
    A segment in the availability timeline.
    
    Represents a continuous period of uptime or downtime.
    
    Attributes:
        start_sec: Start time in seconds from timeline start
        end_sec: End time in seconds from timeline start
        is_up: True for uptime, False for downtime
    """
    start_sec: float
    end_sec: float
    is_up: bool = True
    
    @property
    def duration_sec(self) -> float:
        """Get segment duration in seconds."""
        return self.end_sec - self.start_sec
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for chart data."""
        return {
            "start": self.start_sec,
            "end": self.end_sec,
            "status": "up" if self.is_up else "down",
        }


@dataclass
class EmergencyStatus:
    """
    Emergency stop cause indicators.
    
    Tracks the 10 possible emergency stop sources from ICD state word.
    """
    communication_lost: bool = False       # 통신 두절
    equipment_fail_driving: bool = False   # 장비고장(주행)
    equipment_fail_power: bool = False     # 장비고장(동력계)
    signal_lost_driving: bool = False      # 신호단절(주행)
    signal_lost_autonomous: bool = False   # 신호단절(자율)
    signal_lost_navigation: bool = False   # 신호단절(항법)
    signal_lost_power: bool = False        # 신호단절(동력계)
    signal_lost_comm: bool = False         # 신호단절(통신)
    manual_stop_ocs: bool = False          # 수동정지(운용통제장치)
    manual_stop_near: bool = False         # 수동정지(근거리조종기)
    
    def to_dict(self) -> Dict[str, bool]:
        """Convert to dictionary with Korean labels."""
        return {
            "통신 두절": self.communication_lost,
            "장비고장(주행)": self.equipment_fail_driving,
            "장비고장(동력계)": self.equipment_fail_power,
            "신호단절(주행)": self.signal_lost_driving,
            "신호단절(자율)": self.signal_lost_autonomous,
            "신호단절(항법)": self.signal_lost_navigation,
            "신호단절(동력계)": self.signal_lost_power,
            "신호단절(통신)": self.signal_lost_comm,
            "수동정지(운용통제장치)": self.manual_stop_ocs,
            "수동정지(근거리조종기)": self.manual_stop_near,
        }


@dataclass
class ChartDataPoint:
    """Single data point for time series charts."""
    timestamp: str  # HH:MM:SS format
    pps: int        # Packets per second
    jitter: float   # Jitter in milliseconds


@dataclass
class DashboardState:
    """
    Complete dashboard state for UI rendering.
    
    This is the main state container that gets stored in dcc.Store
    and updated on each polling cycle.
    
    Attributes:
        connected: Overall connection status
        interface: Active network interface name
        filter_desc: Active filter description
        last_packet_time: Timestamp of last received packet
        
        # KPI metrics
        capture_pps: Packets per second captured
        filter_pass_pct: Percentage of packets passing filter
        parse_success_pct: Percentage of successful parses
        checksum_fail_pct: Percentage of checksum failures
        packet_loss_count: Estimated packet loss from seq gaps
        availability_5min: 5-minute availability percentage
        availability_1hour: 1-hour availability percentage
        jitter_p95_ms: 95th percentile jitter
        jitter_p99_ms: 99th percentile jitter
        
        # Operational state
        operation_mode: Current VIC operation mode
        authority: Current authority holder
        driving_state: Current driving state
        
        # Collections
        devices: List of device statuses
        emergency: Emergency status indicators
        chart_data: Time series data points
        availability_segments: Timeline segments
    """
    # Connection info
    connected: bool = True
    interface: str = "lo"
    filter_desc: str = "50000→61000"
    last_packet_time: str = ""
    
    # KPI metrics
    capture_pps: int = 0
    filter_pass_pct: float = 100.0
    parse_success_pct: float = 100.0
    checksum_fail_pct: float = 0.0
    packet_loss_count: int = 0
    availability_5min: float = 100.0
    availability_1hour: float = 100.0
    jitter_p95_ms: float = 0.0
    jitter_p99_ms: float = 0.0
    
    # Operational state
    operation_mode: str = "준비 (PREP)"
    authority: str = "해제됨 (RELEASED)"
    driving_state: str = "원격 (REMOTE)"
    
    # Collections (stored as dicts for JSON serialization)
    devices: List[Dict] = field(default_factory=list)
    emergency_status: Dict[str, bool] = field(default_factory=dict)
    chart_data: List[Dict] = field(default_factory=list)
    availability_segments: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for dcc.Store."""
        return {
            "connected": self.connected,
            "interface": self.interface,
            "filter": self.filter_desc,
            "lastPacketTime": self.last_packet_time,
            "capturePps": self.capture_pps,
            "filterPass": self.filter_pass_pct,
            "parseSuccess": self.parse_success_pct,
            "checksumFail": self.checksum_fail_pct,
            "packetLoss": self.packet_loss_count,
            "availability5min": self.availability_5min,
            "availability1hour": self.availability_1hour,
            "jitterP95": self.jitter_p95_ms,
            "jitterP99": self.jitter_p99_ms,
            "operationalMode": self.operation_mode,
            "operationalAuthority": self.authority,
            "drivingState": self.driving_state,
            "devices": self.devices,
            "emergencyStatus": self.emergency_status,
            "combinedData": self.chart_data,
            "availabilitySegments": self.availability_segments,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DashboardState":
        """Create DashboardState from dictionary (dcc.Store data)."""
        return cls(
            connected=data.get("connected", True),
            interface=data.get("interface", "lo"),
            filter_desc=data.get("filter", "50000→61000"),
            last_packet_time=data.get("lastPacketTime", ""),
            capture_pps=data.get("capturePps", 0),
            filter_pass_pct=data.get("filterPass", 100.0),
            parse_success_pct=data.get("parseSuccess", 100.0),
            checksum_fail_pct=data.get("checksumFail", 0.0),
            packet_loss_count=data.get("packetLoss", 0),
            availability_5min=data.get("availability5min", 100.0),
            availability_1hour=data.get("availability1hour", 100.0),
            jitter_p95_ms=data.get("jitterP95", 0.0),
            jitter_p99_ms=data.get("jitterP99", 0.0),
            operation_mode=data.get("operationalMode", "준비 (PREP)"),
            authority=data.get("operationalAuthority", "해제됨 (RELEASED)"),
            driving_state=data.get("drivingState", "원격 (REMOTE)"),
            devices=data.get("devices", []),
            emergency_status=data.get("emergencyStatus", {}),
            chart_data=data.get("combinedData", []),
            availability_segments=data.get("availabilitySegments", []),
        )
