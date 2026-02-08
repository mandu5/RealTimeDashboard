"""
Scapy 기반 패킷 스니퍼.

네트워크에서 UDP 패킷을 캡처하여 콜백으로 전달합니다.
통계는 StatsService에서 관리합니다.
"""

import logging
import threading
import warnings
from datetime import datetime
from typing import Callable, Optional, Tuple

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from scapy.all import UDP, Raw, sniff
    from scapy.packet import Packet
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    Packet = None

logger = logging.getLogger(__name__)


class PacketSniffer:
    """UDP 패킷 스니퍼.

    네트워크 인터페이스에서 특정 포트의 UDP 패킷을 캡처합니다.
    캡처된 패킷은 (datetime, bytes) 튜플로 콜백에 전달됩니다.

    Args:
        interface: 네트워크 인터페이스 이름 (예: "lo", "eno2")
        src_port: 소스 포트 필터
        dst_port: 목적지 포트 필터
        callback: 패킷 수신 시 호출될 콜백 (Tuple[datetime, bytes] 전달)
    """

    def __init__(
        self,
        interface: str,
        src_port: int,
        dst_port: int,
        callback: Callable[[Tuple[datetime, bytes]], None]
    ):
        if not SCAPY_AVAILABLE:
            raise ImportError("Scapy is not installed. Run: pip install scapy")

        self._interface = interface
        self._src_port = src_port
        self._dst_port = dst_port
        self._callback = callback
        self._filter = f"udp and src port {src_port} and dst port {dst_port}"
        self._running = False
        self._thread: Optional[threading.Thread] = None

        logger.info(f"PacketSniffer initialized: {interface}, filter='{self._filter}'")

    def start(self) -> None:
        """캡처 시작."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, name="PacketSniffer", daemon=True)
        self._thread.start()
        logger.info(f"Sniffer started on '{self._interface}'")

    def stop(self) -> None:
        """캡처 중지."""
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Sniffer stopped")

    def is_running(self) -> bool:
        """캡처 실행 중 여부."""
        return self._running

    def _capture_loop(self) -> None:
        """캡처 루프."""
        try:
            sniff(
                prn=self._process_packet,
                filter=self._filter,
                iface=self._interface,
                store=False,
                stop_filter=lambda _: not self._running
            )
        except PermissionError:
            logger.error("Permission denied. Run with sudo or set cap_net_raw capability.")
            self._running = False
        except OSError as e:
            logger.error(f"OS error: {e}")
            self._running = False
        except Exception as e:
            logger.error(f"Capture error: {e}")
            self._running = False

    def _process_packet(self, packet: Packet) -> None:
        """패킷 처리."""
        try:
            if UDP in packet and Raw in packet:
                capture_time = datetime.now()
                raw_data = bytes(packet[Raw].load)
                self._callback((capture_time, raw_data))
        except Exception as e:
            logger.warning(f"Packet processing error: {e}")

    @property
    def interface(self) -> str:
        """네트워크 인터페이스."""
        return self._interface

    @property
    def filter_str(self) -> str:
        """BPF 필터 문자열."""
        return self._filter
