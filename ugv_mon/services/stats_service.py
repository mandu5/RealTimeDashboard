"""
통계 서비스.

패킷 처리 결과를 집계하고 통계를 제공합니다.
Single Responsibility: 통계 카운터 관리만 수행.

책임:
    1. BatchProcessResult 집계
    2. 파싱률/체크섬률 계산
    3. 마지막 패킷 시간/페이로드 관리
    4. 연결 타임아웃 판단

데이터 흐름:
    Processor.process_pending() → BatchProcessResult → StatsService.update()

사용 예시:
    >>> stats = StatsService()
    >>> stats.update(result)  # BatchProcessResult
    >>> print(stats.get_parse_rate())
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..pipeline import BatchProcessResult

logger = logging.getLogger(__name__)


@dataclass
class StatsSnapshot:
    """통계 스냅샷 (읽기 전용)."""
    total_packets: int
    parse_success: int
    checksum_fail: int
    parse_rate: float
    checksum_fail_rate: float
    is_connected: bool
    last_packet_time: Optional[datetime]


class StatsService:
    """통계 카운터 관리 서비스.

    패킷 처리 결과를 집계하고 통계를 제공합니다.
    상태 관리(연결 여부, 마지막 페이로드)를 포함합니다.

    Args:
        timeout_sec: 연결 타임아웃 초 (이 시간 동안 패킷이 없으면 연결 끊김)
    """

    def __init__(self, timeout_sec: float = 5.0):
        self._timeout_sec = timeout_sec
        self._lock = Lock()

        # 카운터
        self._total_packets = 0
        self._parse_success = 0
        self._checksum_fail = 0

        # 상태
        self._last_packet_time: Optional[datetime] = None
        self._last_payload: Optional[object] = None  # OperationalPayload

    # =========================================================================
    # 업데이트
    # =========================================================================

    def update(self, result: "BatchProcessResult") -> None:
        """BatchProcessResult로 통계 업데이트.

        Args:
            result: PacketProcessor.process_pending()의 반환값
        """
        with self._lock:
            self._total_packets += result.count
            self._parse_success += result.success_count
            self._checksum_fail += result.checksum_fail_count

            if result.last_payload:
                self._last_payload = result.last_payload

            if result.count > 0:
                self._last_packet_time = datetime.now()

    def reset(self) -> None:
        """모든 카운터 초기화."""
        with self._lock:
            self._total_packets = 0
            self._parse_success = 0
            self._checksum_fail = 0
            self._last_packet_time = None
            self._last_payload = None

    # =========================================================================
    # 통계 조회
    # =========================================================================

    def get_parse_rate(self) -> float:
        """파싱 성공률 (0-100%)."""
        with self._lock:
            if self._total_packets == 0:
                return 100.0
            return round((self._parse_success / self._total_packets) * 100, 1)

    def get_checksum_fail_rate(self) -> float:
        """체크섬 오류율 (0-100%)."""
        with self._lock:
            if self._total_packets == 0:
                return 0.0
            return round((self._checksum_fail / self._total_packets) * 100, 1)

    def is_connected(self) -> bool:
        """연결 상태 (타임아웃 기반 판단).

        마지막 패킷 수신 후 timeout_sec 초과 시 False.
        """
        with self._lock:
            if self._last_packet_time is None:
                return False
            elapsed = (datetime.now() - self._last_packet_time).total_seconds()
            return elapsed < self._timeout_sec

    def get_snapshot(self) -> StatsSnapshot:
        """현재 통계 스냅샷 반환."""
        with self._lock:
            return StatsSnapshot(
                total_packets=self._total_packets,
                parse_success=self._parse_success,
                checksum_fail=self._checksum_fail,
                parse_rate=self.get_parse_rate(),
                checksum_fail_rate=self.get_checksum_fail_rate(),
                is_connected=self.is_connected(),
                last_packet_time=self._last_packet_time,
            )

    # =========================================================================
    # 프로퍼티
    # =========================================================================

    @property
    def total_packets(self) -> int:
        """총 패킷 수."""
        with self._lock:
            return self._total_packets

    @property
    def last_packet_time(self) -> Optional[datetime]:
        """마지막 패킷 수신 시간."""
        with self._lock:
            return self._last_packet_time

    @property
    def last_packet_time_str(self) -> str:
        """마지막 패킷 수신 시간 (문자열)."""
        with self._lock:
            if self._last_packet_time:
                return self._last_packet_time.strftime("%H:%M:%S")
            return ""

    @property
    def last_payload(self) -> Optional[object]:
        """마지막 페이로드 (OperationalPayload)."""
        with self._lock:
            return self._last_payload
