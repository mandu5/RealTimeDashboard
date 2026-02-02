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

from ..constants import SEQ_MODULO, EXPECTED_PPS


@dataclass
class PacketRecord:
    """패킷 수신 기록."""
    timestamp: datetime
    sequence: int
    size: int
    jitter_ms: Optional[float] = None


class StatsCalculator:
    """실시간 통계 계산기.
    
    수정 이력:
    - 2026-01-29: window_sec 60→300 변경, 가용성 계산 개선
    - 2026-01-31: msg_code별 sequence 추적, 4비트(0~15) packet loss
    """

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

    def record_packet(self, timestamp: datetime, sequence: int, size: int, msg_code: int = 0) -> Optional[float]:
        """패킷 기록 및 지터 반환."""
        with self._lock:
            jitter_ms = None
            
            # msg_code별로 지터/sequence 계산
            if msg_code not in self._last_by_code:
                self._last_by_code[msg_code] = {"timestamp": None, "interval": None, "sequence": None}
            
            code_data = self._last_by_code[msg_code]
            
            # 지터 계산 (msg_code별) - 5주차: 큰 gap 스킵 + 전역 스킵 카운터
            MAX_GAP_MS = 3000  # 3초 이상 갭은 스트림 재시작으로 간주
            
            if code_data["timestamp"] is not None:
                interval_ms = (timestamp - code_data["timestamp"]).total_seconds() * 1000
                
                if interval_ms > MAX_GAP_MS:
                    # 큰 갭: 스트림 재시작으로 간주, 지터 계산 스킵
                    code_data["interval"] = None  # interval도 리셋!
                    jitter_ms = None
                elif self._global_skip_count > 0:
                    # 포트 전환 후 전역 스킵 (모든 msg_code에 적용)
                    self._global_skip_count -= 1
                    code_data["interval"] = None  # interval도 리셋! (버그 수정)
                    jitter_ms = None
                else:
                    if code_data["interval"] is not None:
                        # 지터 = |현재 간격 - 이전 간격|
                        jitter_ms = abs(interval_ms - code_data["interval"])
                    code_data["interval"] = interval_ms  # 정상 케이스에서만 interval 저장
            
            code_data["timestamp"] = timestamp  # 반드시 저장 (지터 0 문제 해결)
            
            # packet loss 계산 (msg_code별, 4비트 sequence)
            if code_data["sequence"] is not None:
                gap = self._seq_gap(code_data["sequence"], sequence)
                if gap > 1:
                    if msg_code not in self._loss_by_code:
                        self._loss_by_code[msg_code] = 0
                    self._loss_by_code[msg_code] += (gap - 1)
            
            code_data["sequence"] = sequence

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
        """패킷 손실 (msg_code별 누적합)."""
        with self._lock:
            return sum(self._loss_by_code.values())

    def _seq_gap(self, prev_seq: int, curr_seq: int) -> int:
        """4비트(0~15) 롤오버 고려한 시퀀스 갭."""
        prev_seq = prev_seq & 0x0F
        curr_seq = curr_seq & 0x0F
        diff = (curr_seq - prev_seq) % 16
        # 너무 큰 점프(8 이상)는 재시작으로 간주하고 손실로 세지 않음
        if diff > 8:
            return 1  # 점프지만 손실 아님
        return diff

    def get_availability(self, window_sec: Optional[int] = None) -> float:
        """
        가용성 계산 - 최근 N분간 연결 시간 비율.
        
        5분 이상이면 window 기준, 미만이면 실제 경과 시간 기준.
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
            
            first_packet_time = records_in_window[0].timestamp
            
            # 5분 이상이면 window 기준, 미만이면 실제 경과 시간 기준
            if first_packet_time <= cutoff:
                # 첫 패킷이 cutoff 이전 = window만큼 데이터 있음
                actual_duration = window
            else:
                # 첫 패킷 ~ 현재
                actual_duration = (now - first_packet_time).total_seconds()
            
            # 측정 구간이 너무 짧으면 100% 반환
            if actual_duration < 1.0:
                return 100.0
            
            # 연결 상태 시간 계산
            TIMEOUT_SEC = 1.5
            
            connected_time = 0.0
            for i in range(len(records_in_window) - 1):
                gap = (records_in_window[i + 1].timestamp - records_in_window[i].timestamp).total_seconds()
                if gap <= TIMEOUT_SEC:
                    connected_time += gap
            
            # 마지막 패킷 ~ 현재까지도 계산
            last_gap = (now - records_in_window[-1].timestamp).total_seconds()
            if last_gap <= TIMEOUT_SEC:
                connected_time += last_gap
            
            availability = (connected_time / actual_duration) * 100
            return min(round(availability, 2), 100.0)

    def get_pps(self) -> int:
        """현재 PPS."""
        with self._lock:
            if not self._records:
                return 0
            one_sec_ago = datetime.now() - timedelta(seconds=1)
            return sum(1 for r in self._records if r.timestamp >= one_sec_ago)

    def get_current_jitter(self) -> float:
        """현재 지터 (가장 최근 유효 값)."""
        with self._lock:
            for r in reversed(self._records):
                if r.jitter_ms is not None:
                    return round(r.jitter_ms, 2)
            return 0.0

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
            self._loss_by_code.clear()
            self._global_skip_count = 0

    def reset_stream_state(self, clear_records: bool = False, skip_samples: int = 3) -> None:
        """스트림 상태만 리셋 (방향 전환 시 호출).
        
        Args:
            clear_records: 기록도 삭제할지 여부
            skip_samples: 리셋 후 스킵할 지터 샘플 수 (기본 3)
        """
        with self._lock:
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

