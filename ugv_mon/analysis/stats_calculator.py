"""
실시간 통계 계산기 - PPS, 지터, 패킷 손실, 가용성.

수정 이력:
- 2026-01-28: 지터를 간격 변동(|현재 간격 - 이전 간격|)으로 계산
- 2026-01-28: 가용성을 패킷 수 기반 → 연결 상태(간격) 기반으로 변경
- 2026-01-28: msg_code별 지터 계산 분리
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
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
        self._last_interval: Optional[float] = None
        self._max_sequence = MAX_SEQUENCE
        self._lock = threading.Lock()
        
        # msg_code별 마지막 timestamp/interval 저장
        self._last_by_code: Dict[int, Dict] = {}

    def record_packet(self, timestamp: datetime, sequence: int, size: int, msg_code: int = 0) -> Optional[float]:
        """패킷 기록 및 지터 반환."""
        with self._lock:
            jitter_ms = None
            
            # msg_code별로 지터 계산
            if msg_code not in self._last_by_code:
                self._last_by_code[msg_code] = {"timestamp": None, "interval": None}
            
            code_data = self._last_by_code[msg_code]
            
            if code_data["timestamp"] is not None:
                interval_ms = (timestamp - code_data["timestamp"]).total_seconds() * 1000
                
                if code_data["interval"] is not None:
                    # 지터 = |현재 간격 - 이전 간격|
                    jitter_ms = abs(interval_ms - code_data["interval"])
                
                code_data["interval"] = interval_ms
            
            code_data["timestamp"] = timestamp

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
        """
        가용성 계산 - 패킷 수신 간격 기반.
        
        패킷 간격이 TIMEOUT 이내면 "연결됨"으로 간주하고,
        연결된 시간 / 전체 측정 시간으로 가용성 계산.
        """
        with self._lock:
            if not self._records:
                return 0.0

            now = datetime.now()
            window = window_sec or self._window_sec
            cutoff = now - timedelta(seconds=window)
            
            # 윈도우 내 패킷만 필터
            records_in_window = [r for r in self._records if r.timestamp >= cutoff]
            
            if not records_in_window:
                return 0.0
            
            # 실제 측정 구간 = 첫 패킷 ~ 현재
            first_packet_time = records_in_window[0].timestamp
            actual_duration = (now - first_packet_time).total_seconds()
            
            # 측정 구간이 너무 짧으면 100% 반환
            if actual_duration < 1.0:
                return 100.0
            
            # 연결 상태 시간 계산
            # 패킷 간격이 TIMEOUT 이내면 "연결됨"으로 간주
            TIMEOUT_SEC = 1.5  # 1초마다 패킷이 오니까 1.5초로 설정
            
            connected_time = 0.0
            for i in range(len(records_in_window) - 1):
                gap = (records_in_window[i + 1].timestamp - records_in_window[i].timestamp).total_seconds()
                if gap <= TIMEOUT_SEC:
                    connected_time += gap
            
            # 마지막 패킷 ~ 현재까지도 계산
            last_gap = (now - records_in_window[-1].timestamp).total_seconds()
            if last_gap <= TIMEOUT_SEC:
                connected_time += last_gap
            
            # 실제 측정 구간 기준으로 계산
            availability = (connected_time / actual_duration) * 100
            return min(round(availability, 2), 100.0)

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
            self._last_interval = None
            self._last_by_code.clear()

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

