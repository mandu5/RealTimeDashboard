"""
캡처 서비스.

패킷 캡처 시작/중지/방향 전환만 담당합니다.
Single Responsibility: 캡처 제어만 수행.

책임:
    1. PacketSniffer 생성 및 관리
    2. 캡처 시작/중지
    3. 캡처 방향 전환 (VIC→OCS / OCS→VIC)

사용 예시:
    >>> capture = CaptureService("lo", queue)
    >>> capture.start()
    >>> capture.toggle_direction()
    >>> capture.stop()
"""

import logging
from threading import Lock
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..pipeline import PacketQueue, PacketSniffer

logger = logging.getLogger(__name__)


class CaptureService:
    """패킷 캡처 제어 서비스.

    캡처 시작/중지/방향전환만 담당합니다.
    상태 관리나 통계 집계는 하지 않습니다.

    Args:
        interface: 네트워크 인터페이스 이름 (예: "lo", "eno2")
        queue: 패킷을 저장할 큐
        vic_port: VIC 포트 (기본: 50000)
        ocs_port: OCS 포트 (기본: 61000)
    """

    def __init__(
        self,
        interface: str,
        queue: "PacketQueue",
        vic_port: int = 50000,
        ocs_port: int = 61000,
    ):
        self._interface = interface
        self._queue = queue
        self._vic_port = vic_port
        self._ocs_port = ocs_port

        # 현재 캡처 방향
        self._direction = "status"  # "status" = VIC→OCS, "control" = OCS→VIC
        self._src_port = vic_port
        self._dst_port = ocs_port

        # 스니퍼
        self._sniffer: Optional["PacketSniffer"] = None
        self._lock = Lock()

    # =========================================================================
    # 캡처 제어
    # =========================================================================

    def start(self) -> bool:
        """캡처 시작.

        Returns:
            성공 여부
        """
        with self._lock:
            if self._sniffer:
                self._cleanup_sniffer()

            try:
                from ..pipeline import PacketSniffer

                self._sniffer = PacketSniffer(
                    self._interface,
                    self._src_port,
                    self._dst_port,
                    self._queue.put,
                )
                self._sniffer.start()
                logger.info(
                    f"Capture started: {self._interface} "
                    f"({self._src_port}→{self._dst_port})"
                )
                return True
            except (PermissionError, OSError) as e:
                logger.error(f"Capture failed: {e}")
                return False

    def stop(self) -> None:
        """캡처 중지."""
        with self._lock:
            self._cleanup_sniffer()
            logger.info("Capture stopped")

    def toggle(self) -> bool:
        """캡처 시작/중지 토글.

        Returns:
            토글 후 실행 중 여부
        """
        if self.is_running:
            self.stop()
            return False
        else:
            return self.start()

    def toggle_direction(self) -> str:
        """캡처 방향 전환.

        status: VIC → OCS (상태 메시지)
        control: OCS → VIC (제어 메시지)

        Returns:
            새로운 방향 ("status" 또는 "control")
        """
        with self._lock:
            was_running = self._sniffer is not None
            if was_running:
                self._cleanup_sniffer()

            # 방향 전환
            if self._direction == "status":
                self._direction = "control"
                self._src_port = self._ocs_port
                self._dst_port = self._vic_port
            else:
                self._direction = "status"
                self._src_port = self._vic_port
                self._dst_port = self._ocs_port

            logger.info(
                f"Direction changed: {self._direction} "
                f"({self._src_port}→{self._dst_port})"
            )

        # 기존에 실행 중이었으면 다시 시작
        if was_running:
            self.start()

        return self._direction

    # =========================================================================
    # 상태 조회
    # =========================================================================

    @property
    def is_running(self) -> bool:
        """캡처 실행 중 여부."""
        with self._lock:
            return self._sniffer is not None and self._sniffer.is_running()

    @property
    def direction(self) -> str:
        """현재 캡처 방향."""
        return self._direction

    @property
    def interface(self) -> str:
        """네트워크 인터페이스."""
        return self._interface

    @property
    def filter_str(self) -> str:
        """현재 BPF 필터 문자열."""
        return f"{self._src_port}→{self._dst_port}"

    # =========================================================================
    # 내부 메서드
    # =========================================================================

    def _cleanup_sniffer(self) -> None:
        """스니퍼 정리 (락 없이 호출됨)."""
        if self._sniffer:
            try:
                if self._sniffer.is_running():
                    self._sniffer.stop()
            except OSError as e:
                logger.warning(f"[Capture] 스니퍼 정리 중 OS 오류: {e}")
            except Exception as e:
                logger.warning(f"[Capture] 스니퍼 정리 중 예외: {e}")
            self._sniffer = None
