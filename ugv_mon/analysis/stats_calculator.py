"""실시간 통계 계산기 - PPS, 지터, 패킷 손실, 가용성 계산."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from collections import deque
import threading
import logging

logger = logging.getLogger(__name__)

MAX_GAP_MS = 3000         # 3초 이상 갭 → 스트림 재시작
MAX_JITTER_MS = 200       # 200ms 이상 지터 → 이상치 (P95/P99 필터용)
JITTER_THRESHOLD_MS = 5   # 5ms 초과 interval 변화 시 지터 스킵


@dataclass(frozen=True)
class PacketRecord:
    """패킷 기록."""
    timestamp: datetime
    sequence: int
    size: int
    jitter_ms: Optional[float]


class StatsCalculator:
    """실시간 통계 계산기."""

    def __init__(self, window_sec: int = 300):
        self._window_sec = window_sec
        self._lock = threading.Lock()
        self._records: deque = deque()
        self._last_timestamp: Optional[datetime] = None
        self._last_sequence: Optional[int] = None
        self._last_by_code: Dict[int, Dict] = {}
        self._loss_by_code: Dict[int, int] = {}

    def record_packet(self, timestamp: datetime, sequence: int, size: int, msg_code: int = 0) -> Optional[float]:
        """패킷 기록 및 지터 반환."""
        with self._lock:
            if msg_code not in self._last_by_code:
                self._last_by_code[msg_code] = {"timestamp": None, "interval": None, "sequence": None}
            code_data = self._last_by_code[msg_code]
            
            self._calculate_packet_loss(code_data, sequence, msg_code)
            jitter_ms = self._calculate_jitter(timestamp, code_data)
            
            # 상태 저장
            code_data["timestamp"] = timestamp
            code_data["sequence"] = sequence
            
            self._records.append(PacketRecord(timestamp, sequence, size, jitter_ms))
            self._last_timestamp = timestamp
            self._last_sequence = sequence
            self._prune_old_records(timestamp)
            
            return jitter_ms

    def _calculate_jitter(self, timestamp: datetime, code_data: Dict) -> Optional[float]:
        """지터 계산 (회사 로직 반영).
        
        조건:
        1. 첫 패킷이면 스킵
        2. interval > MAX_GAP_MS면 스킵, interval 리셋
        3. prev_interval이 없거나 비정상이면 스킵
        4. interval - prev_interval > 5ms면 스킵 (급격한 변화)
        """
        # 첫 패킷
        if code_data["timestamp"] is None:
            return None
        
        interval_ms = (timestamp - code_data["timestamp"]).total_seconds() * 1000
        
        # 큰 갭은 스킵
        if interval_ms > MAX_GAP_MS:
            code_data["interval"] = None
            return None
        
        # 이전 interval 확인
        prev_interval = code_data.get("interval")
        
        if prev_interval is not None and prev_interval <= MAX_GAP_MS:
            # 둘 다 정상 범위일 때만 지터 계산
            jitter_ms = abs(interval_ms - prev_interval)
            
            # interval 변화가 5ms 초과면 지터 스킵 (급격한 변화)
            if interval_ms - prev_interval > JITTER_THRESHOLD_MS:
                jitter_ms = None
        else:
            # 이전 값이 없거나 비정상이면 지터 스킵
            jitter_ms = None
        
        # 현재 interval 저장
        code_data["interval"] = interval_ms
        
        return jitter_ms

    def _calculate_packet_loss(self, code_data: Dict, sequence: int, msg_code: int):
        """패킷 손실 계산."""
        if code_data["sequence"] is not None:
            gap = self._seq_gap(code_data["sequence"], sequence)
            if gap > 1:
                self._loss_by_code[msg_code] = self._loss_by_code.get(msg_code, 0) + (gap - 1)

    def _seq_gap(self, prev: int, curr: int) -> int:
        """4비트 롤오버 고려한 시퀀스 갭."""
        return ((curr & 0x0F) - (prev & 0x0F)) % 16

    def _prune_old_records(self, current_time: datetime):
        """윈도우 밖 기록 제거."""
        cutoff = current_time - timedelta(seconds=self._window_sec)
        while self._records and self._records[0].timestamp < cutoff:
            self._records.popleft()

    # 통계 조회
    def get_stats_dict(self) -> dict:
        p95, p99 = self.get_jitter_percentiles()
        return {
            "pps": self.get_pps(),
            "jitter_current": self.get_current_jitter(),
            "jitter_p95": p95, "jitter_p99": p99,
            "packet_loss": self.get_packet_loss(),
            "availability": self.get_availability(),
        }

    def get_jitter_percentiles(self) -> Tuple[float, float]:
        """지터 P95, P99."""
        with self._lock:
            jitters = [r.jitter_ms for r in self._records 
                       if r.jitter_ms is not None and r.jitter_ms <= MAX_JITTER_MS]
            if not jitters:
                return (0.0, 0.0)
            sorted_j = sorted(jitters)
            n = len(sorted_j)
            return (round(sorted_j[min(int(n * 0.95), n-1)], 2), 
                    round(sorted_j[min(int(n * 0.99), n-1)], 2))

    def get_current_jitter(self) -> float:
        with self._lock:
            for r in reversed(self._records):
                if r.jitter_ms is not None and r.jitter_ms <= MAX_JITTER_MS:
                    return round(r.jitter_ms, 2)
            return 0.0

    def get_average_jitter(self) -> float:
        with self._lock:
            jitters = [r.jitter_ms for r in self._records 
                       if r.jitter_ms is not None and r.jitter_ms <= MAX_JITTER_MS]
            return round(sum(jitters) / len(jitters), 2) if jitters else 0.0

    def get_pps(self) -> int:
        with self._lock:
            if not self._records:
                return 0
            one_sec_ago = datetime.now() - timedelta(seconds=1)
            return sum(1 for r in self._records if r.timestamp >= one_sec_ago)

    def get_packet_loss(self) -> int:
        with self._lock:
            return sum(self._loss_by_code.values())

    def get_availability(self) -> float:
        with self._lock:
            if not self._records:
                return 0.0
            window_start = datetime.now() - timedelta(seconds=self._window_sec)
            recent = [r for r in self._records if r.timestamp >= window_start]
            if len(recent) < 2:
                return 0.0
            expected = 100 * self._window_sec
            return round(min(len(recent) / expected * 100, 100), 1)

    # 상태 제어
    def reset(self):
        with self._lock:
            self._records.clear()
            self._last_timestamp = self._last_sequence = None
            self._last_by_code.clear()
            self._loss_by_code.clear()

    def reset_stream_state(self, clear_records: bool = False, skip_samples: int = 0):
        """스트림 상태 리셋 (포트/연결 전환 시 호출)."""
        with self._lock:
            logger.info(f"[STATS] reset_stream_state: clear={clear_records}")
            self._last_by_code.clear()
            self._loss_by_code.clear()
            if clear_records:
                self._records.clear()
