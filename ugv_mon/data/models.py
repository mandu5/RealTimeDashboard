"""
UGV-MON 대시보드 데이터 모델.

Dashboard 상태, 로그 엔트리, 장치 상태 등의 타입 정의.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class OperationMode(Enum):
    """VIC 운용 모드 (bits 7..5)."""
    PREP = 0b000
    TRANSITION = 0b001
    UNMANNED_DRIVING = 0b010
    UNMANNED_FIRING = 0b011
    EMERGENCY_STOP = 0b100
    UNKNOWN = 0xFF


class Authority(Enum):
    """VIC 운용 권한 (bits 3..2)."""
    RELEASED = 0b00
    OCS_ACQUIRED = 0b01
    NEAR_CONTROLLER = 0b10
    UNKNOWN = 0xFF


class DrivingState(Enum):
    """VIC 주행 상태 (bits 1..0)."""
    REMOTE = 0b01
    PLATOONING = 0b10
    AUTONOMOUS_DISPATCH = 0b11
    UNKNOWN = 0xFF


@dataclass
class DeviceStatus:
    """장치 연결 상태."""
    device_id: str
    name: str
    connected: bool = True
    warning: bool = False
    last_seen: Optional[datetime] = None
    error_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.device_id,
            "name": self.name,
            "connected": self.connected,
            "warning": self.warning,
            "error_reason": self.error_reason,
        }


@dataclass
class LogEntry:
    """로그 테이블 엔트리."""
    timestamp: datetime
    sequence: int
    msg_code: str
    parse_ok: bool = True
    checksum_ok: bool = True
    mode: str = ""
    authority: str = ""
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "time": self.timestamp.strftime("%H:%M:%S"),
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
    """가용성 타임라인 세그먼트."""
    start_sec: float
    end_sec: float
    is_up: bool = True

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec

    def to_dict(self) -> Dict:
        return {
            "start": self.start_sec,
            "end": self.end_sec,
            "status": "up" if self.is_up else "down",
        }


@dataclass
class EmergencyStatus:
    """비상정지 원인 상태."""
    communication_lost: bool = False
    equipment_fail_driving: bool = False
    equipment_fail_power: bool = False
    signal_lost_driving: bool = False
    signal_lost_autonomous: bool = False
    signal_lost_navigation: bool = False
    signal_lost_power: bool = False
    signal_lost_comm: bool = False
    manual_stop_ocs: bool = False
    manual_stop_near: bool = False

    def to_dict(self) -> Dict[str, bool]:
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
