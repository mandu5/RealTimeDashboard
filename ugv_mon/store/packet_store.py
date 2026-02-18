"""
통합 패킷 저장소.

모든 패킷 데이터를 단일 deque에 저장하고,
용도에 맞게 변환하여 제공합니다.

데이터 흐름:
    PacketProcessor → PacketStore.add() → deque[PacketRecord]
                                              │
                                              ├── get_stats_dict()         → 통계
                                              ├── get_logs()               → 로그 UI
                                              ├── get_chart_data()         → 차트 UI
                                              ├── get_connection_history() → 연결 이력
                                              └── get_mode_transitions()   → 모드 전이

기존 모듈 대체:
    - stats_calculator.py의 통계 계산 기능
    - live_provider.py의 deque 저장 기능
"""

import logging
import threading
from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Optional

from ..constants import (
    JITTER_NOISE_THRESHOLD_MS,
    JITTER_OUTLIER_THRESHOLD_MS,
    MAX_CONNECTION_HISTORY,
    MAX_MODE_TRANSITIONS,
    STREAM_RESTART_GAP_MS,
)

logger = logging.getLogger(__name__)


class NetworkMetrics:
    """네트워크 메트릭 계산기 (지터/패킷 손실).

    PacketStore에서 네트워크 수학 로직을 분리한 클래스.
    msg_code별 이전 패킷 상태를 추적하여 RFC 3550 기반 지터와
    시퀀스 갭 기반 패킷 손실을 계산합니다.
    """

    def __init__(self) -> None:
        self._prev_by_msgcode: dict[int, dict] = {}
        self._loss_by_msgcode: dict[int, int] = {}

    def calculate(
        self,
        timestamp: datetime,
        msg_code: int,
        sequence: int,
    ) -> tuple[Optional[float], Optional[float]]:
        """지터와 간격 계산 후 패킷 손실도 업데이트.

        Args:
            timestamp: 패킷 수신 시각
            msg_code: ICD 메시지 코드
            sequence: 시퀀스 번호 (0~15)

        Returns:
            (jitter_ms, interval_ms) — 계산 불가 시 None
        """
        if msg_code not in self._prev_by_msgcode:
            self._prev_by_msgcode[msg_code] = {
                "timestamp": None,
                "interval": None,
                "sequence": None,
            }

        state = self._prev_by_msgcode[msg_code]
        prev_ts = state["timestamp"]

        if prev_ts is None:
            state["timestamp"] = timestamp
            state["sequence"] = sequence
            return None, None

        interval_ms = (timestamp - prev_ts).total_seconds() * 1000
        state["timestamp"] = timestamp

        # 큰 갭 스킵 (스트림 재시작으로 간주)
        if interval_ms > STREAM_RESTART_GAP_MS:
            state["interval"] = None
            state["sequence"] = sequence
            return None, interval_ms

        # 지터 계산
        prev_interval = state["interval"]
        jitter_ms: Optional[float] = None
        if isinstance(prev_interval, (int, float)) and prev_interval <= STREAM_RESTART_GAP_MS:
            diff = abs(interval_ms - prev_interval)
            if diff <= JITTER_NOISE_THRESHOLD_MS:
                jitter_ms = diff

        state["interval"] = interval_ms

        # 패킷 손실 계산 (시퀀스 갭, 4-bit 순환)
        prev_seq = state["sequence"]
        state["sequence"] = sequence
        if prev_seq is not None:
            gap = ((sequence & 0x0F) - (prev_seq & 0x0F)) % 16
            if gap > 1:
                self._loss_by_msgcode[msg_code] = (
                    self._loss_by_msgcode.get(msg_code, 0) + (gap - 1)
                )

        return jitter_ms, interval_ms

    def get_total_loss(self) -> int:
        """총 패킷 손실 수."""
        return sum(self._loss_by_msgcode.values())

    def reset(self) -> None:
        """상태 초기화."""
        self._prev_by_msgcode.clear()
        self._loss_by_msgcode.clear()


@dataclass
class PacketRecord:
    """통합 패킷 레코드.

    통계 계산과 UI 표시에 필요한 모든 필드를 포함합니다.

    Attributes:
        timestamp: 패킷 캡처 시각
        msg_code: ICD 메시지 코드
        sequence: 시퀀스 번호 (0~15)
        size: 패킷 크기 (bytes)
        jitter_ms: 지터 값 (ms)
        interval_ms: 패킷 간격 (ms)
        parse_ok: 파싱 성공 여부
        checksum_ok: 체크섬 검증 성공 여부
        operation_mode: 운용 모드
        authority: 운용 권한
    """
    timestamp: datetime
    msg_code: int
    sequence: int
    size: int
    jitter_ms: Optional[float]
    interval_ms: Optional[float]
    parse_ok: bool
    checksum_ok: bool
    operation_mode: str = "---"
    authority: str = "---"

    def to_log_dict(self) -> dict:
        """로그 표시용 Dict 변환 (Live 모드 AG-Grid field명과 일치)."""
        return {
            "timestamp": self.timestamp.strftime("%H:%M:%S"),
            "sequence": self.sequence,
            "msg_code": f"0x{self.msg_code:02X}",
            "parse_ok": "✓" if self.parse_ok else "✗",
            "checksum_ok": "✓" if self.checksum_ok else "✗",
            "mode": self.operation_mode,
            "authority": self.authority,
            "error": "" if self.parse_ok else "파싱 실패",
        }

    def to_chart_point(self, pps: int) -> dict:
        """차트 데이터 포인트 변환."""
        jitter = self.jitter_ms if self.jitter_ms and self.jitter_ms <= JITTER_OUTLIER_THRESHOLD_MS else 0
        return {
            "timestamp": self.timestamp.strftime("%H:%M:%S"),
            "pps": pps,
            "jitter": round(jitter, 2),
        }


class PacketStore:
    """통합 패킷 저장소.

    단일 deque에 모든 패킷 데이터를 저장하고,
    통계 계산 및 UI 표시용 데이터를 제공합니다.

    Attributes:
        window_sec: 데이터 보관 윈도우 (초, 기본 3600)
        max_records: 최대 레코드 수 (기본 360000)
    """

    def __init__(self, window_sec: int = 3600, max_records: int = 360000):
        self._window_sec = window_sec
        self._records: deque[PacketRecord] = deque(maxlen=max_records)
        self._lock = threading.Lock()

        # 네트워크 메트릭 계산기 (지터/패킷 손실)
        self._metrics = NetworkMetrics()

        # 차트 데이터 캐시 (1초 TTL)
        self._chart_cache: list[dict] = []
        self._chart_cache_time: Optional[datetime] = None

        # 연결 이력
        self._connection_history: list[dict] = []
        self._last_connection_state: Optional[bool] = None

        # 모드 전이 이력
        self._mode_transitions: list[dict] = []
        self._last_op_mode: Optional[str] = None

        # 비상정지 통계
        self._emergency_counts: dict[str, int] = {}

    # =========================================================================
    # 패킷 추가
    # =========================================================================

    def add(self, record: PacketRecord) -> Optional[float]:
        """패킷 추가 및 지터 반환.

        Args:
            record: 패킷 레코드

        Returns:
            계산된 지터 (ms), 계산 불가시 None
        """
        with self._lock:
            jitter_ms, interval_ms = self._metrics.calculate(
                record.timestamp, record.msg_code, record.sequence
            )
            updated_record = replace(record, jitter_ms=jitter_ms, interval_ms=interval_ms)
            self._records.append(updated_record)
            self._prune_old_records(record.timestamp)
            return jitter_ms

    def _prune_old_records(self, current_time: datetime) -> None:
        """오래된 레코드 제거."""
        cutoff = current_time - timedelta(seconds=self._window_sec)
        while self._records and self._records[0].timestamp < cutoff:
            self._records.popleft()

    # =========================================================================
    # 통계 조회 (stats_calculator 대체)
    # =========================================================================

    def _get_pps_unlocked(self) -> int:
        """초당 패킷 수 (최근 1초, 락 없이 호출)."""
        if not self._records:
            return 0
        one_sec_ago = datetime.now() - timedelta(seconds=1)
        return sum(1 for r in self._records if r.timestamp >= one_sec_ago)

    def get_pps(self) -> int:
        """초당 패킷 수 (최근 1초)."""
        with self._lock:
            return self._get_pps_unlocked()

    def get_current_jitter(self) -> float:
        """현재(최신) 지터 값."""
        with self._lock:
            for r in reversed(self._records):
                if r.jitter_ms is not None and r.jitter_ms <= JITTER_OUTLIER_THRESHOLD_MS:
                    return round(r.jitter_ms, 2)
            return 0.0

    def get_jitter_p95(self) -> float:
        """지터 P95 반환."""
        with self._lock:
            jitters = [
                r.jitter_ms for r in self._records
                if r.jitter_ms is not None and r.jitter_ms <= JITTER_OUTLIER_THRESHOLD_MS
            ]
            if not jitters:
                return 0.0
            sorted_j = sorted(jitters)
            n = len(sorted_j)
            return round(sorted_j[min(int(n * 0.95), n - 1)], 2)

    def get_packet_loss(self) -> int:
        """총 패킷 손실 수."""
        with self._lock:
            return self._metrics.get_total_loss()

    def get_availability(self, window_sec: int = 300) -> float:
        """가용성 계산 (%)."""
        with self._lock:
            if not self._records:
                return 0.0
            window_start = datetime.now() - timedelta(seconds=window_sec)
            recent = [r for r in self._records if r.timestamp >= window_start]
            if len(recent) < 2:
                return 0.0
            expected = 100 * window_sec
            return round(min(len(recent) / expected * 100, 100), 1)

    def get_stats_dict(self) -> dict:
        """전체 통계 딕셔너리."""
        return {
            "pps": self.get_pps(),
            "jitter_current": self.get_current_jitter(),
            "jitter_p95": self.get_jitter_p95(),
            "packet_loss": self.get_packet_loss(),
            "availability": self.get_availability(),
        }

    def get_stats_history(self, limit: int = 200) -> list[dict]:
        """ML 학습용 통계 히스토리 반환.

        최근 N개의 레코드에서 ML 특성 추출에 필요한 통계를 반환합니다.

        Args:
            limit: 반환할 최대 레코드 수

        Returns:
            [{"jitter_current": ..., "pps": ..., ...}, ...]
        """
        with self._lock:
            if not self._records:
                return []

            result = []
            records_list = list(self._records)[-limit:]

            for _i, r in enumerate(records_list):
                jitter = r.jitter_ms if r.jitter_ms is not None else 0
                result.append({
                    "timestamp": r.timestamp.isoformat(),
                    "jitter_current": jitter,
                    "jitter_p95": jitter,  # 개별 레코드에서는 P95 계산 불가
                    "pps": 1,  # 개별 레코드
                    "loss_rate": 0,  # 집계 후 계산
                    "parse_success_rate": 100.0 if r.parse_ok else 0.0,
                    "checksum_fail_rate": 100.0 if not r.checksum_ok else 0.0,
                })

            return result

    # =========================================================================
    # UI 데이터 조회 (live_provider deque 대체)
    # =========================================================================

    def get_logs(self, limit: int = 50) -> list[dict]:
        """로그 표시용 데이터."""
        with self._lock:
            recent = list(self._records)[-limit:]
            return [r.to_log_dict() for r in reversed(recent)]

    def get_chart_data(self, limit: int = 180) -> list[dict]:
        """차트 표시용 데이터."""
        with self._lock:
            # 캐시 확인 (1초 이내면 캐시 반환)
            now = datetime.now()
            if (self._chart_cache_time and
                (now - self._chart_cache_time).total_seconds() < 1):
                return self._chart_cache

            # 초당 집계
            if not self._records:
                return []

            pps = self._get_pps_unlocked()
            recent = list(self._records)[-limit:]
            result = [r.to_chart_point(pps) for r in recent]

            # 캐시 갱신
            self._chart_cache = result
            self._chart_cache_time = now

            return result

    def get_parse_success_rate(self) -> float:
        """파싱 성공률 (%)."""
        with self._lock:
            if not self._records:
                return 0.0
            success = sum(1 for r in self._records if r.parse_ok)
            return round(success / len(self._records) * 100, 1)

    def get_checksum_fail_rate(self) -> float:
        """체크섬 실패율 (%)."""
        with self._lock:
            if not self._records:
                return 0.0
            fail = sum(1 for r in self._records if not r.checksum_ok)
            return round(fail / len(self._records) * 100, 1)

    # =========================================================================
    # 이력 관리
    # =========================================================================

    def record_connection_change(self, connected: bool) -> None:
        """연결 상태 변경 기록."""
        with self._lock:
            if self._last_connection_state == connected:
                return

            now = datetime.now()

            # 이전 항목에 duration 계산
            if self._connection_history:
                prev = self._connection_history[-1]
                if prev.get("duration") is None:
                    prev_time = datetime.fromisoformat(prev["timestamp"])
                    prev["duration"] = round((now - prev_time).total_seconds(), 1)

            self._connection_history.append({
                "timestamp": now.isoformat(),
                "connected": connected,
                "duration": None,
            })
            self._connection_history = self._connection_history[-MAX_CONNECTION_HISTORY:]

            self._last_connection_state = connected

    def record_mode_transition(self, new_mode: str) -> None:
        """운용 모드 전이 기록."""
        with self._lock:
            if self._last_op_mode and self._last_op_mode != new_mode:
                self._mode_transitions.append({
                    "timestamp": datetime.now().isoformat(),
                    "from": self._last_op_mode,
                    "to": new_mode,
                })

                self._mode_transitions = self._mode_transitions[-MAX_MODE_TRANSITIONS:]

            self._last_op_mode = new_mode

    def record_emergency(self, reasons: list[str]) -> None:
        """비상정지 원인 기록."""
        with self._lock:
            for reason in reasons:
                self._emergency_counts[reason] = (
                    self._emergency_counts.get(reason, 0) + 1
                )

    def get_connection_history(self, limit: int = 10) -> list[dict]:
        """연결 이력."""
        with self._lock:
            return self._connection_history[-limit:]

    def get_mode_transitions(self, limit: int = 10) -> list[dict]:
        """모드 전이 이력."""
        with self._lock:
            return self._mode_transitions[-limit:]

    def get_emergency_counts(self) -> dict[str, int]:
        """비상정지 원인별 카운트."""
        with self._lock:
            return dict(self._emergency_counts)

    # =========================================================================
    # 상태 제어
    # =========================================================================

    def reset(self) -> None:
        """전체 상태 초기화."""
        with self._lock:
            self._records.clear()
            self._metrics.reset()
            self._chart_cache.clear()
            self._chart_cache_time = None
            self._connection_history.clear()
            self._last_connection_state = None
            self._mode_transitions.clear()
            self._last_op_mode = None
            self._emergency_counts.clear()

    def reset_stream_state(self) -> None:
        """스트림 상태만 리셋 (방향 전환 시 지터 오염 방지)."""
        with self._lock:
            logger.info("[STORE] reset_stream_state")
            self._metrics.reset()

    @property
    def record_count(self) -> int:
        """현재 저장된 레코드 수."""
        with self._lock:
            return len(self._records)
