"""
패킷 캡처 통계.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CaptureStats:
    """캡처 통계."""
    packets_total: int = 0
    packets_filtered: int = 0
    bytes_total: int = 0
    start_time: Optional[datetime] = None
    last_packet_time: Optional[datetime] = None

    # PPS 계산용
    _pps_window_start: Optional[datetime] = field(default=None, repr=False)
    _pps_window_count: int = field(default=0, repr=False)
    _current_pps: int = field(default=0, repr=False)

    def record_packet(self, size: int, filtered: bool = True) -> None:
        """패킷 기록."""
        now = datetime.now()
        self.packets_total += 1
        self.bytes_total += size

        if filtered:
            self.packets_filtered += 1

        if self.start_time is None:
            self.start_time = now
        self.last_packet_time = now
        self._update_pps(now)

    def _update_pps(self, now: datetime) -> None:
        """PPS 업데이트."""
        if self._pps_window_start is None:
            self._pps_window_start = now
            self._pps_window_count = 1
            return

        elapsed = (now - self._pps_window_start).total_seconds()
        if elapsed >= 1.0:
            self._current_pps = self._pps_window_count
            self._pps_window_start = now
            self._pps_window_count = 1
        else:
            self._pps_window_count += 1

    def get_pps(self) -> int:
        return self._current_pps

    def get_filter_pass_pct(self) -> float:
        if self.packets_total == 0:
            return 100.0
        return (self.packets_filtered / self.packets_total) * 100.0

    def reset(self) -> None:
        """통계 초기화."""
        self.packets_total = 0
        self.packets_filtered = 0
        self.bytes_total = 0
        self.start_time = None
        self.last_packet_time = None
        self._pps_window_start = None
        self._pps_window_count = 0
        self._current_pps = 0

    def to_dict(self) -> dict:
        return {
            "packets_total": self.packets_total,
            "packets_filtered": self.packets_filtered,
            "bytes_total": self.bytes_total,
            "pps": self.get_pps(),
            "filter_pass_pct": round(self.get_filter_pass_pct(), 1),
            "last_packet_time": self.last_packet_time.strftime("%H:%M:%S") if self.last_packet_time else "",
        }
