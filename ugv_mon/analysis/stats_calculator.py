"""
실시간 통계 계산기.

패킷 기록, PPS, 지터, 패킷 손실, 가용성 계산.
5주차: 지터 오염 방지 로직 강화 (7가지 방어층)
"""

from dataclasses import dataclass
from datetime import datetime, timedeltaㅇ
from typing import Optional, Tuple, List, Dict
from collections import deque
import threading
import logging

from ..constants import SEQ_MODULO

logger = logging.getLogger(__name__)

# =============================================================================
# 지터 관련 상수 (5주차 강화)
# =============================================================================
MAX_GAP_MS = 3000       # 3초 이상 갭은 스트림 재시작으로 간주
MAX_JITTER_MS = 200     # 200ms 이상 지터는 이상치로 간주 (정상: 0~50ms)
MAX_INTERVAL_MS = 2000  # 2초 이상 interval은 비정상
INITIAL_SKIP_COUNT = 5  # 스트림 시작 후 첫 5개 지터 스킵


@dataclass(frozen=True)
class PacketRecord:
    """패킷 기록."""
    timestamp: datetime
    sequence: int
    size: int
    jitter_ms: Optional[float]


class StatsCalculator:
    """실시간 통계 계산기 (지터 오염 7중 방어)."""

    def __init__(self, window_sec: int = 300):  # 5분으로 변경
        self._window_sec = window_sec
        self._records: deque = deque()
        self._last_timestamp: Optional[datetime] = None
        self._last_sequence: Optional[int] = None
        self._last_interval: Optional[float] = None
        self._max_sequence = 16  # 4비트: 0~15 (변경됨)
        self._lock = threading.Lock()
        
        # msg_code별 마지막 timestamp/interval/sequence 저장
        self._last_by_code: Dict[int, Dict] = {}
        # msg_code별 packet loss 누적
        self._loss_by_code: Dict[int, int] = {}
        # 전역 지터 스킵 카운터 (포트 전환 후 첫 N개 샘플 스킵)
        self._global_skip_count: int = 0
        
        # 디버깅용 카운터 (5주차)
        self._debug_counts = {
            "total_packets": 0,
            "skipped_max_gap": 0,
            "skipped_global": 0,
            "skipped_max_jitter": 0,
            "skipped_max_interval": 0,
            "skipped_first_interval": 0,
            "valid_jitter": 0,
        }

    def record_packet(self, timestamp: datetime, sequence: int, size: int, msg_code: int = 0) -> Optional[float]:
        """패킷 기록 및 지터 반환.
        
        7가지 방어층:
        1. 첫 패킷 (이전 timestamp 없음) - 스킵
        2. MAX_GAP_MS (3초) 이상 갭 - 스킵
        3. global_skip_count (포트 전환 후 5개) - 스킵
        4. MAX_INTERVAL_MS (2초) 이상 interval - 스킵
        5. 첫 interval (이전 interval 없음) - 스킵
        6. MAX_JITTER_MS (200ms) 이상 지터 - None으로 마스킹
        7. P95/P99 계산 시 추가 필터링
        """
        with self._lock:
            self._debug_counts["total_packets"] += 1
            jitter_ms = None
            
            # msg_code별로 지터/sequence 계산
            if msg_code not in self._last_by_code:
                self._last_by_code[msg_code] = {"timestamp": None, "interval": None, "sequence": None}
            
            code_data = self._last_by_code[msg_code]
            
            # === 패킷 손실 계산 (모든 분기에서 수행) ===
            self._calculate_packet_loss(code_data, sequence, msg_code)
            
            # === 방어층 1: 첫 패킷 (이전 timestamp 없음) ===
            if code_data["timestamp"] is None:
                code_data["timestamp"] = timestamp
                code_data["sequence"] = sequence
                self._finalize_record(timestamp, sequence, size, None)
                return None
            
            # interval 계산
            interval_ms = (timestamp - code_data["timestamp"]).total_seconds() * 1000
            
            # === 방어층 2: MAX_GAP_MS (3초) 이상 갭 ===
            if interval_ms > MAX_GAP_MS:
                self._debug_log("MAX_GAP", interval_ms, msg_code)
                self._debug_counts["skipped_max_gap"] += 1
                code_data["interval"] = None
                code_data["timestamp"] = timestamp
                code_data["sequence"] = sequence
                self._finalize_record(timestamp, sequence, size, None)
                return None
            
            # === 방어층 3: global_skip_count (포트 전환 후 N개) ===
            if self._global_skip_count > 0:
                self._debug_log("GLOBAL_SKIP", interval_ms, msg_code, self._global_skip_count)
                self._debug_counts["skipped_global"] += 1
                self._global_skip_count -= 1
                code_data["interval"] = None  # interval도 리셋!
                code_data["timestamp"] = timestamp
                code_data["sequence"] = sequence
                self._finalize_record(timestamp, sequence, size, None)
                return None
            
            # === 방어층 4: MAX_INTERVAL_MS (2초) 이상 interval ===
            if interval_ms > MAX_INTERVAL_MS:
                self._debug_log("MAX_INTERVAL", interval_ms, msg_code)
                self._debug_counts["skipped_max_interval"] += 1
                code_data["interval"] = None
                code_data["timestamp"] = timestamp
                code_data["sequence"] = sequence
                self._finalize_record(timestamp, sequence, size, None)
                return None
            
            # === 방어층 5: 첫 interval (이전 interval 없음) ===
            if code_data["interval"] is None:
                self._debug_counts["skipped_first_interval"] += 1
                code_data["interval"] = interval_ms
                code_data["timestamp"] = timestamp
                code_data["sequence"] = sequence
                self._finalize_record(timestamp, sequence, size, None)
                return None
            
            # === 지터 계산 ===
            jitter_ms = abs(interval_ms - code_data["interval"])
            
            # === 방어층 6: MAX_JITTER_MS (200ms) 이상 지터 ===
            if jitter_ms > MAX_JITTER_MS:
                self._debug_log("MAX_JITTER", jitter_ms, msg_code, interval_ms, code_data["interval"])
                self._debug_counts["skipped_max_jitter"] += 1
                code_data["interval"] = interval_ms  # interval은 저장 (다음 계산에 사용)
                code_data["timestamp"] = timestamp
                code_data["sequence"] = sequence
                self._finalize_record(timestamp, sequence, size, None)  # None 저장!
                return None
            
            # === 정상 지터 ===
            self._debug_counts["valid_jitter"] += 1
            code_data["interval"] = interval_ms
            code_data["timestamp"] = timestamp
            code_data["sequence"] = sequence

            self._finalize_record(timestamp, sequence, size, jitter_ms)
            return jitter_ms

    def _calculate_packet_loss(self, code_data: Dict, sequence: int, msg_code: int) -> None:
        """패킷 손실 계산 (msg_code별, 4비트 sequence)."""
        if code_data["sequence"] is not None:
            gap = self._seq_gap(code_data["sequence"], sequence)
            if gap > 1:
                if msg_code not in self._loss_by_code:
                    self._loss_by_code[msg_code] = 0
                self._loss_by_code[msg_code] += (gap - 1)

    def _finalize_record(self, timestamp: datetime, sequence: int, size: int, jitter_ms: Optional[float]) -> None:
        """레코드 저장 및 정리."""
        self._records.append(PacketRecord(timestamp, sequence, size, jitter_ms))
        self._last_timestamp = timestamp
        self._last_sequence = sequence
        self._prune_old_records(timestamp)

    def _debug_log(self, reason: str, value: float, msg_code: int, *extra):
        """디버깅 로그 출력."""
        extra_str = f", extra={extra}" if extra else ""
        logger.debug(f"[JITTER_SKIP] {reason}: {value:.2f}ms, msg=0x{msg_code:02X}{extra_str}")

    def _prune_old_records(self, current_time: datetime) -> None:
        """오래된 기록 제거."""
        cutoff = current_time - timedelta(seconds=self._window_sec)
        while self._records and self._records[0].timestamp < cutoff:
            self._records.popleft()

    def get_jitter_percentiles(self) -> Tuple[float, float]:
        """지터 P95, P99 계산 (방어층 7: 추가 필터링)."""
        with self._lock:
            # None 제외 + MAX_JITTER_MS 이하만 사용 (이중 필터링)
            jitters = [
                r.jitter_ms for r in self._records 
                if r.jitter_ms is not None and r.jitter_ms <= MAX_JITTER_MS
            ]
            if not jitters:
                return (0.0, 0.0)

            sorted_jitters = sorted(jitters)
            n = len(sorted_jitters)
            p95 = sorted_jitters[min(int(n * 0.95), n - 1)]
            p99 = sorted_jitters[min(int(n * 0.99), n - 1)]
            return (round(p95, 2), round(p99, 2))

    def get_packet_loss(self) -> int:
        """패킷 손실 (msg_code별 누적합)."""
        with self._lock:
            return sum(self._loss_by_code.values())

    def _seq_gap(self, prev_seq: int, curr_seq: int) -> int:
        """4비트(0~15) 롤오버 고려한 시퀀스 갭."""
        prev_seq = prev_seq & 0x0F
        curr_seq = curr_seq & 0x0F
        diff = (curr_seq - prev_seq) % 16
        return diff if diff != 0 else 0

    def get_availability(self) -> float:
        """가용성 % 계산."""
        with self._lock:
            if not self._records:
                return 0.0
            
            now = datetime.now()
            window_start = now - timedelta(seconds=self._window_sec)
            
            recent = [r for r in self._records if r.timestamp >= window_start]
            if len(recent) < 2:
                return 0.0
            
            expected_pps = 100
            expected_packets = expected_pps * self._window_sec
            actual_packets = len(recent)
            
            return round(min(actual_packets / expected_packets * 100, 100), 1)

    def get_pps(self) -> int:
        """초당 패킷 수 계산."""
        with self._lock:
            if not self._records:
                return 0
            
            now = datetime.now()
            one_sec_ago = now - timedelta(seconds=1)
            recent = [r for r in self._records if r.timestamp >= one_sec_ago]
            return len(recent)

    def get_current_jitter(self) -> float:
        """현재(가장 최근) 유효한 지터 값."""
        with self._lock:
            for r in reversed(self._records):
                if r.jitter_ms is not None and r.jitter_ms <= MAX_JITTER_MS:
                    return round(r.jitter_ms, 2)
            return 0.0

    def get_average_jitter(self) -> float:
        """평균 지터 (필터링 적용)."""
        with self._lock:
            jitters = [
                r.jitter_ms for r in self._records 
                if r.jitter_ms is not None and r.jitter_ms <= MAX_JITTER_MS
            ]
            return round(sum(jitters) / len(jitters), 2) if jitters else 0.0

    def reset(self) -> None:
        with self._lock:
            self._records.clear()
            self._last_timestamp = None
            self._last_sequence = None
            self._last_interval = None
            self._last_by_code.clear()
            self._loss_by_code.clear()
            self._global_skip_count = 0
            self._debug_counts = {k: 0 for k in self._debug_counts}

    def reset_stream_state(self, clear_records: bool = False, skip_samples: int = INITIAL_SKIP_COUNT) -> None:
        """스트림 상태만 리셋 (방향/연결 전환 시 호출).
        
        Args:
            clear_records: 기록도 삭제할지 여부
            skip_samples: 리셋 후 스킵할 지터 샘플 수 (기본 5)
        """
        with self._lock:
            logger.info(f"[JITTER] reset_stream_state called, skip={skip_samples}, clear={clear_records}")
            # 전역 스킵 카운터 설정 (모든 msg_code에 적용)
            self._global_skip_count = skip_samples
            self._last_by_code.clear()
            self._loss_by_code.clear()
            if clear_records:
                self._records.clear()

    def get_stats_dict(self) -> dict:
        """전체 통계 딕셔너리."""
        p95, p99 = self.get_jitter_percentiles()
        availability = self.get_availability()  # 한 번만 호출
        
        packet_loss = self.get_packet_loss()  # 캐싱: 한 번만 호출
        
        return {
            "pps": self.get_pps(),
            "jitter_current": self.get_current_jitter(),  # 5주차: avg → current
            "jitter_p95": p95,
            "jitter_p99": p99,
            "packet_loss": packet_loss,
            "availability": availability,
        }

    def get_debug_stats(self) -> dict:
        """디버깅용 통계 반환."""
        with self._lock:
            return {
                **self._debug_counts,
                "global_skip_remaining": self._global_skip_count,
                "records_count": len(self._records),
                "msg_codes": list(self._last_by_code.keys()),
            }
