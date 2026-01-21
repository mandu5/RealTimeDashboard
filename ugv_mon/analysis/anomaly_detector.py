"""
이상 탐지기 - 지터, 패킷 손실, 타임아웃 탐지.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
import threading


class AnomalyType(Enum):
    """이상 유형."""
    HIGH_JITTER = "high_jitter"
    PACKET_LOSS = "packet_loss"
    CONNECTION_TIMEOUT = "connection_timeout"
    CHECKSUM_ERROR = "checksum_error"


@dataclass
class Anomaly:
    """탐지된 이상."""
    type: AnomalyType
    timestamp: datetime
    message: str
    value: Optional[float] = None
    severity: str = "warning"

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.strftime("%H:%M:%S"),
            "message": self.message,
            "value": self.value,
            "severity": self.severity,
        }


class AnomalyDetector:
    """이상 탐지기."""

    def __init__(
        self,
        jitter_warning: float = 10.0,
        jitter_error: float = 50.0,
        timeout_sec: float = 5.0,
    ):
        self._jitter_warning = jitter_warning
        self._jitter_error = jitter_error
        self._timeout_sec = timeout_sec
        self._recent_anomalies: List[Anomaly] = []
        self._lock = threading.Lock()

    def check_jitter(self, jitter_ms: float) -> Optional[Anomaly]:
        """지터 이상 탐지."""
        if jitter_ms is None:
            return None

        anomaly = None
        if jitter_ms >= self._jitter_error:
            anomaly = Anomaly(
                type=AnomalyType.HIGH_JITTER,
                timestamp=datetime.now(),
                message=f"심각한 지터: {jitter_ms:.1f}ms",
                value=jitter_ms,
                severity="error"
            )
        elif jitter_ms >= self._jitter_warning:
            anomaly = Anomaly(
                type=AnomalyType.HIGH_JITTER,
                timestamp=datetime.now(),
                message=f"높은 지터: {jitter_ms:.1f}ms",
                value=jitter_ms,
                severity="warning"
            )

        if anomaly:
            self._add_anomaly(anomaly)
        return anomaly

    def check_timeout(self, last_packet_time: Optional[datetime]) -> Optional[Anomaly]:
        """타임아웃 탐지."""
        if last_packet_time is None:
            return None

        elapsed = (datetime.now() - last_packet_time).total_seconds()
        if elapsed >= self._timeout_sec:
            anomaly = Anomaly(
                type=AnomalyType.CONNECTION_TIMEOUT,
                timestamp=datetime.now(),
                message=f"연결 타임아웃: {elapsed:.1f}초",
                value=elapsed,
                severity="error"
            )
            self._add_anomaly(anomaly)
            return anomaly
        return None

    def check_packet_loss(self, prev_seq: int, curr_seq: int) -> Optional[Anomaly]:
        """패킷 손실 탐지."""
        gap = curr_seq - prev_seq if curr_seq >= prev_seq else (256 - prev_seq) + curr_seq
        if gap > 1:
            lost = gap - 1
            anomaly = Anomaly(
                type=AnomalyType.PACKET_LOSS,
                timestamp=datetime.now(),
                message=f"패킷 손실: {lost}개",
                value=lost,
                severity="warning" if lost < 5 else "error"
            )
            self._add_anomaly(anomaly)
            return anomaly
        return None

    def _add_anomaly(self, anomaly: Anomaly) -> None:
        with self._lock:
            self._recent_anomalies.insert(0, anomaly)
            self._recent_anomalies = self._recent_anomalies[:100]

    def get_recent_anomalies(self, limit: int = 10) -> List[Anomaly]:
        with self._lock:
            return self._recent_anomalies[:limit]

    def clear_anomalies(self) -> None:
        with self._lock:
            self._recent_anomalies.clear()
