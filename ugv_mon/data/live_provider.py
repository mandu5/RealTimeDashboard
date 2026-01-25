"""
Live Data Provider - 실시간 패킷 캡처 및 파싱 통합.
MockDataGenerator와 동일한 인터페이스로 모드 전환 가능.
"""

import logging
import os
import subprocess
import platform
from collections import deque
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional

from ..config import config
from ..constants import DEVICE_IDS, DEVICE_NAMES
from .models import LogEntry, DeviceStatus, AvailabilitySegment, EmergencyStatus

logger = logging.getLogger(__name__)

try:
    from ..capture import PacketSniffer, PacketQueue
    from ..parser import ICDParser
    from ..analysis import StatsCalculator, AnomalyDetector
    CAPTURE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Capture modules not available: {e}")
    CAPTURE_AVAILABLE = False


class LiveDataProvider:
    """실시간 데이터 제공자."""

    def __init__(self, interface: str = None):
        self._interface = interface or os.getenv("UGV_MON_INTERFACE") or config.network.interface
        self._src_port = config.network.source_port
        self._dst_port = config.network.dest_port
        self._lock = Lock()
        
        # 캡처 컴포넌트
        self._packet_queue: Optional[PacketQueue] = None
        self._sniffer: Optional[PacketSniffer] = None
        self._parser: Optional[ICDParser] = None
        self._stats_calc: Optional[StatsCalculator] = None
        
        # 상태
        self._logs: deque = deque(maxlen=config.ui.max_log_entries)
        self._chart_data: deque = deque(maxlen=config.ui.max_chart_points)
        self._is_connected = False
        self._last_packet_time: Optional[datetime] = None
        
        # 운용 상태
        self._mode = "준비 (PREP)"
        self._authority = "해제됨 (RELEASED)"
        self._driving = "원격 (REMOTE)"
        self._devices: List[DeviceStatus] = []
        self._emergency = EmergencyStatus()
        
        # 통계
        self._total_packets = 0
        self._parse_success = 0
        self._checksum_fail = 0
        
        if CAPTURE_AVAILABLE:
            self._init_modules()

    def _init_modules(self):
        self._packet_queue = PacketQueue(max_size=1000)
        self._parser = ICDParser()
        self._stats_calc = StatsCalculator(window_sec=60)

    # =========================================================================
    # 캡처 제어
    # =========================================================================
    
    def start_capture(self) -> bool:
        if not CAPTURE_AVAILABLE:
            return False
        if self._sniffer:
            self._cleanup_sniffer()
        try:
            self._sniffer = PacketSniffer(self._interface, self._src_port, self._dst_port, self._packet_queue.put)
            self._sniffer.start()
            self._is_connected = True
            logger.info(f"Capture started on: {self._interface}")
            return True
        except (PermissionError, OSError) as e:
            logger.error(f"Capture failed: {e}")
            return False

    def stop_capture(self):
        self._cleanup_sniffer()
        self._is_connected = False

    def _cleanup_sniffer(self):
        if self._sniffer:
            try:
                if self._sniffer.is_running():
                    self._sniffer.stop()
            except Exception:
                pass
            self._sniffer = None

    def switch_interface(self, new_interface: str) -> bool:
        with self._lock:
            if new_interface == self._interface:
                return True
            was_running = self._is_connected
            if was_running:
                self.stop_capture()
            old = self._interface
            self._interface = new_interface
            if was_running:
                if not self.start_capture():
                    self._interface = old
                    self.start_capture()
                    return False
            return True

    def toggle_connection(self) -> bool:
        with self._lock:
            if self._is_connected:
                self.stop_capture()
                return False
            return self.start_capture()

    def get_available_interfaces(self) -> List[str]:
        try:
            if platform.system() == "Linux":
                result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True, timeout=5)
                return [l.split(": ")[1].split("@")[0] for l in result.stdout.split("\n") if ": " in l and "@" not in l.split(": ")[1]] or ["lo", "eth0"]
            elif platform.system() == "Darwin":
                result = subprocess.run(["networksetup", "-listallhardwareports"], capture_output=True, text=True, timeout=5)
                return ["lo0"] + [l.replace("Device:", "").strip() for l in result.stdout.split("\n") if l.startswith("Device:")]
            return ["lo", "eth0"]
        except Exception:
            return ["lo", "eno2", "eno3"]

    # =========================================================================
    # 데이터 생성/업데이트
    # =========================================================================
    
    def generate_initial_data(self) -> Dict:
        self._devices = [DeviceStatus(did, name.upper(), False) for did, name in zip(DEVICE_IDS, DEVICE_NAMES)]
        return self._build_state()

    def update_data(self, prev_data: Dict) -> Dict:
        with self._lock:
            self._process_packets()
            self._check_timeout()
            self._update_chart()
            return self._build_state()

    def _process_packets(self):
        if not self._packet_queue or not self._parser:
            return
        for raw in self._packet_queue.get_all():
            self._process_packet(raw)

    def _process_packet(self, raw: bytes):
        now = datetime.now()
        self._total_packets += 1
        result = self._parser.parse(raw)
        
        if result.success:
            self._parse_success += 1
        if not result.checksum_ok:
            self._checksum_fail += 1
        
        if result.success and result.header and self._stats_calc:
            self._stats_calc.record_packet(now, result.header.sequence, len(raw))
        
        if result.success and result.payload:
            self._update_from_payload(result.payload)
        
        seq = result.header.sequence if result.header else 0
        msg = f"0x{result.header.msg_code:02X}" if result.header else "???"
        self._logs.appendleft(LogEntry(now, seq, msg, result.success, result.checksum_ok, self._mode, self._authority, "" if result.success else (result.error or "실패")))
        self._last_packet_time = now
        self._is_connected = True

    def _update_from_payload(self, p):
        self._mode = p.operation_mode_label
        self._authority = p.authority_label
        self._driving = p.driving_state_label
        self._devices = [DeviceStatus(did, name, p.devices.get(name, False), None if p.devices.get(name) else "연결 안 됨") for did, name in zip(DEVICE_IDS, DEVICE_NAMES)]
        es = EmergencyStatus()
        mapping = [("communication_lost", "통신 두절"), ("equipment_fail_driving", "장비고장(주행)"), ("equipment_fail_power", "장비고장(동력계)"),
                   ("signal_lost_driving", "신호단절(주행)"), ("signal_lost_autonomous", "신호단절(자율)"), ("signal_lost_navigation", "신호단절(항법)"),
                   ("signal_lost_power", "신호단절(동력계)"), ("signal_lost_comm", "신호단절(통신)"), ("manual_stop_ocs", "수동정지(운용통제장치)"), ("manual_stop_near", "수동정지(근거리조종기)")]
        for attr, key in mapping:
            setattr(es, attr, p.emergency_status.get(key, False))
        self._emergency = es

    def _check_timeout(self):
        if self._last_packet_time and (datetime.now() - self._last_packet_time).total_seconds() >= config.ui.down_threshold_sec:
            self._is_connected = False

    def _update_chart(self):
        now = datetime.now()
        stats = self._stats_calc.get_stats_dict() if self._stats_calc else {}
        self._chart_data.append({"timestamp": now.strftime("%H:%M:%S"), "pps": stats.get("pps", 0), "jitter": stats.get("jitter_avg", 0.0)})

    def _build_state(self) -> Dict:
        stats = self._stats_calc.get_stats_dict() if self._stats_calc else {}
        return {
            "connected": self._is_connected, "interface": self._interface,
            "filter": f"{self._src_port}→{self._dst_port}",
            "lastPacketTime": self._last_packet_time.strftime("%H:%M:%S") if self._last_packet_time else "",
            "capturePps": stats.get("pps", 0), "filterPass": 100.0,
            "parseSuccess": round((self._parse_success / max(self._total_packets, 1)) * 100, 1),
            "checksumFail": round((self._checksum_fail / max(self._total_packets, 1)) * 100, 1),
            "packetLoss": stats.get("packet_loss", 0),
            "availability5min": stats.get("availability", 0.0), "availability1hour": stats.get("availability", 0.0),
            "jitterP95": stats.get("jitter_p95", 0.0), "jitterP99": stats.get("jitter_p99", 0.0),
            "operationalMode": self._mode, "operationalAuthority": self._authority, "drivingState": self._driving,
            "combinedData": list(self._chart_data),
            "devices": [d.to_dict() for d in self._devices],
            "emergencyStatus": self._emergency.to_dict(),
            "availabilitySegments": [{"start": 0, "end": config.ui.timeline_duration_sec, "isUp": self._is_connected}],
        }

    def get_logs(self, limit: int = 50) -> List[Dict]:
        with self._lock:
            return [log.to_dict() for log in list(self._logs)[:limit]]

    def clear_logs(self):
        with self._lock:
            self._logs.clear()

    @property
    def log_count(self) -> int:
        return len(self._logs)
