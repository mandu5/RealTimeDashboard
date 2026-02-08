"""
Scapy 기반 패킷 스니퍼.
"""

import logging
import threading
import warnings
from datetime import datetime
from typing import Callable, Optional

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from scapy.all import UDP, Raw, sniff
    from scapy.packet import Packet
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    Packet = None

from .stats import CaptureStats

logger = logging.getLogger(__name__)


class PacketSniffer:
    """UDP 패킷 스니퍼."""

    def __init__(
        self,
        interface: str,
        src_port: int,
        dst_port: int,
        callback: Callable[[bytes], None]
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
        self._stats = CaptureStats()

        logger.info(f"PacketSniffer initialized: {interface}, filter='{self._filter}'")

    def start(self) -> None:
        """캡처 시작."""
        if self._running:
            return

        self._running = True
        self._stats.reset()
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
        return self._running

    def get_stats(self) -> CaptureStats:
        return self._stats

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
                capture_time = datetime.now()  # 캡처 시점 저장
                raw_data = bytes(packet[Raw].load)
                self._stats.record_packet(len(raw_data), filtered=True)
                self._callback((capture_time, raw_data))  # 튜플로 전달
        except Exception as e:
            logger.warning(f"Packet processing error: {e}")

    @property
    def interface(self) -> str:
        return self._interface

    @property
    def filter_str(self) -> str:
        return self._filter
