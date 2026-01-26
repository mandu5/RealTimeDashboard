"""
실시간 통계 계산기 - PPS, 지터, 패킷 손실, 가용성.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple
import threading

from ..constants import MAX_SEQUENCE, EXPECTED_PPS


@dataclass
class PacketRecord:
    """패킷 수신 기록."""
    timestamp: datetime
    sequence: int
    size: int
    jitter_ms: Optional[float] = None


class StatsCalculator:
    """실시간 통계 계산기."""

    def __init__(self, window_sec: int = 60):
        self._window_sec = window_sec
        self._records: deque = deque()
        self._last_timestamp: Optional[datetime] = None
        self._last_sequence: Optional[int] = None
        self._max_sequence = MAX_SEQUENCE
        self._lock = threading.Lock()

    def record_packet(self, timestamp: datetime, sequence: int, size: int) -> Optional[float]:
        """패킷 기록 및 지터 반환."""
        with self._lock:
            jitter_ms = None
            if self._last_timestamp is not None:
                time_diff = (timestamp - self._last_timestamp).total_seconds() * 1000
                jitter_ms = abs(time_diff)

            self._records.append(PacketRecord(timestamp, sequence, size, jitter_ms))
            self._last_timestamp = timestamp
            self._last_sequence = sequence
            self._prune_old_records(timestamp)
            return jitter_ms

    def _prune_old_records(self, current_time: datetime) -> None:
        """오래된 기록 제거."""
        cutoff = current_time - timedelta(seconds=self._window_sec)
        while self._records and self._records[0].timestamp < cutoff:
            self._records.popleft()

    def get_jitter_percentiles(self) -> Tuple[float, float]:
        """지터 P95, P99 계산."""
        with self._lock:
            jitters = [r.jitter_ms for r in self._records if r.jitter_ms is not None]
            if not jitters:
                return (0.0, 0.0)

            sorted_jitters = sorted(jitters)
            n = len(sorted_jitters)
            p95 = sorted_jitters[min(int(n * 0.95), n - 1)]
            p99 = sorted_jitters[min(int(n * 0.99), n - 1)]
            return (round(p95, 2), round(p99, 2))

    def get_packet_loss(self) -> int:
        """패킷 손실 추정."""
        with self._lock:
            if len(self._records) < 2:
                return 0

            total_loss = 0
            records_list = list(self._records)
            for i in range(1, len(records_list)):
                prev_seq = records_list[i - 1].sequence
                curr_seq = records_list[i].sequence
                gap = self._seq_gap(prev_seq, curr_seq)
                if gap > 1:
                    total_loss += (gap - 1)
            return total_loss

    def _seq_gap(self, prev_seq: int, curr_seq: int) -> int:
        """롤오버 고려한 시퀀스 갭."""
        if curr_seq >= prev_seq:
            return curr_seq - prev_seq
        return (self._max_sequence - prev_seq) + curr_seq

    def get_availability(self, window_sec: Optional[int] = None) -> float:
        """가용성 계산."""
        with self._lock:
            if not self._records:
                return 100.0

            now = datetime.now()
            window = window_sec or self._window_sec
            cutoff = now - timedelta(seconds=window)
            packets_in_window = sum(1 for r in self._records if r.timestamp >= cutoff)

            expected_packets = window * EXPECTED_PPS
            return min(round((packets_in_window / max(expected_packets, 1)) * 100, 2), 100.0)

    def get_pps(self) -> int:
        """현재 PPS."""
        with self._lock:
            if not self._records:
                return 0
            one_sec_ago = datetime.now() - timedelta(seconds=1)
            return sum(1 for r in self._records if r.timestamp >= one_sec_ago)

    def get_average_jitter(self) -> float:
        """평균 지터."""
        with self._lock:
            jitters = [r.jitter_ms for r in self._records if r.jitter_ms is not None]
            return round(sum(jitters) / len(jitters), 2) if jitters else 0.0

    def reset(self) -> None:
        with self._lock:
            self._records.clear()
            self._last_timestamp = None
            self._last_sequence = None

    def get_stats_dict(self) -> dict:
        """전체 통계 딕셔너리."""
        p95, p99 = self.get_jitter_percentiles()
        return {
            "pps": self.get_pps(),
            "jitter_avg": self.get_average_jitter(),
            "jitter_p95": p95,
            "jitter_p99": p99,
            "packet_loss": self.get_packet_loss(),
            "availability": self.get_availability(),
        }
