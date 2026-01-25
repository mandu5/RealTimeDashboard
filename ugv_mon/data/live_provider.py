"""
Live Data Provider - 실시간 패킷 캡처 및 파싱 통합.

PacketSniffer + ICDParser를 연결하여 대시보드에 데이터 제공.
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

# 캡처/파서 모듈 (선택적 임포트)
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

        # 캡처 컴포넌트
        self._packet_queue: Optional[PacketQueue] = None
        self._sniffer: Optional[PacketSniffer] = None
        self._parser: Optional[ICDParser] = None
        self._stats_calc: Optional[StatsCalculator] = None
        self._anomaly_detector: Optional[AnomalyDetector] = None

        # 상태 저장
        self._logs_history: deque = deque(maxlen=config.ui.max_log_entries)
        self._chart_data: deque = deque(maxlen=config.ui.max_chart_points)
        self._availability_segments: List[AvailabilitySegment] = []

        # 현재 상태
        self._is_connected = False
        self._last_packet_time: Optional[datetime] = None
        self._last_sequence: Optional[int] = None

        # 운용 상태
        self._current_mode = "준비 (PREP)"
        self._current_authority = "해제됨 (RELEASED)"
        self._current_driving = "원격 (REMOTE)"
        self._current_devices: List[DeviceStatus] = []
        self._current_emergency = EmergencyStatus()

        # 통계
        self._total_packets = 0
        self._parse_success = 0
        self._checksum_fail = 0
        self._elapsed_time = 0.0
        self._lock = Lock()

        if CAPTURE_AVAILABLE:
            self._init_modules()

    def _init_modules(self) -> None:
        """모듈 초기화."""
        self._packet_queue = PacketQueue(max_size=1000)
        self._parser = ICDParser()
        self._stats_calc = StatsCalculator(window_sec=60)
        self._anomaly_detector = AnomalyDetector()

    def start_capture(self) -> bool:
        """패킷 캡처 시작."""
        if not CAPTURE_AVAILABLE:
            logger.error("Capture modules not available")
            return False

        # 기존 sniffer 정리 (리소스 누수 방지)
        if self._sniffer is not None:
            self._cleanup_sniffer()

        try:
            self._sniffer = PacketSniffer(
                interface=self._interface,
                src_port=self._src_port,
                dst_port=self._dst_port,
                callback=self._packet_queue.put
            )
            self._sniffer.start()
            self._is_connected = True
            logger.info(f"Capture started on interface: {self._interface}")
            return True
        except PermissionError as e:
            logger.error(f"Permission denied for packet capture: {e}")
            logger.error("Run with sudo or set CAP_NET_RAW capability")
            return False
        except OSError as e:
            logger.error(f"OS error starting capture: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to start capture: {e}")
            return False

    def _cleanup_sniffer(self) -> None:
        """기존 sniffer 정리."""
        if self._sniffer is not None:
            try:
                if self._sniffer.is_running():
                    self._sniffer.stop()
                logger.debug("Previous sniffer cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up sniffer: {e}")
            finally:
                self._sniffer = None

    def stop_capture(self) -> None:
        """패킷 캡처 중지."""
        self._cleanup_sniffer()
        self._is_connected = False

    def switch_interface(self, new_interface: str) -> bool:
        """
        인터페이스 전환.
        
        Args:
            new_interface: 새로운 네트워크 인터페이스 (예: "lo", "eno2", "eno3")
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if new_interface == self._interface:
                return True  # 이미 같은 인터페이스
            
            logger.info(f"Switching interface from {self._interface} to {new_interface}")
            
            # 기존 캡처 중지
            was_running = self._is_connected
            if was_running:
                self.stop_capture()
            
            # 새 인터페이스로 설정
            old_interface = self._interface
            self._interface = new_interface
            
            # 새 인터페이스로 캡처 재시작
            if was_running:
                success = self.start_capture()
                if not success:
                    # 실패 시 이전 인터페이스로 복구
                    logger.error(f"Failed to start capture on {new_interface}, reverting to {old_interface}")
                    self._interface = old_interface
                    self.start_capture()  # 이전 인터페이스로 복구 시도
                    return False
                logger.info(f"Interface switched successfully to {new_interface}")
                return True
            else:
                # 캡처가 실행 중이 아니었으면 설정만 변경
                logger.info(f"Interface set to {new_interface} (capture not running)")
                return True

    def toggle_connection(self) -> bool:
        """
        연결 상태 토글 (시작/중지).
        
        Returns:
            True if connected, False if disconnected
        """
        with self._lock:
            if self._is_connected:
                logger.info("Stopping packet capture...")
                self.stop_capture()
                return False
            else:
                logger.info("Starting packet capture...")
                success = self.start_capture()
                return success

    def get_available_interfaces(self) -> List[str]:
        """
        사용 가능한 네트워크 인터페이스 목록 반환.
        
        Returns:
            인터페이스 이름 리스트
        """
        try:
            system = platform.system()
            if system == "Linux":
                result = subprocess.run(
                    ["ip", "link", "show"],
                    capture_output=True, text=True, timeout=5
                )
                interfaces = []
                for line in result.stdout.split("\n"):
                    if ": " in line and "@" not in line:
                        parts = line.split(": ")
                        if len(parts) >= 2:
                            interface = parts[1].split("@")[0]
                            interfaces.append(interface)
                return interfaces if interfaces else ["lo", "eth0"]
            elif system == "Darwin":  # macOS
                result = subprocess.run(
                    ["networksetup", "-listallhardwareports"],
                    capture_output=True, text=True, timeout=5
                )
                interfaces = ["lo0"]  # loopback always available
                for line in result.stdout.split("\n"):
                    if line.startswith("Device:"):
                        interface = line.replace("Device:", "").strip()
                        interfaces.append(interface)
                return interfaces if len(interfaces) > 1 else ["lo0", "en0"]
            else:
                return ["lo", "eth0"]  # Fallback
        except Exception as e:
            logger.warning(f"Failed to get interfaces dynamically: {e}")
            return ["lo", "eno2", "eno3"]  # Fallback to hardcoded

    def generate_initial_data(self) -> Dict:
        """초기 데이터 생성."""
        self._current_devices = [
            DeviceStatus(device_id, name.upper(), connected=False)
            for device_id, name in zip(DEVICE_IDS, DEVICE_NAMES)
        ]
        self._availability_segments = [
            AvailabilitySegment(0, config.ui.timeline_duration_sec, is_up=False)
        ]

        return self._build_state_dict()

    def update_data(self, prev_data: Dict) -> Dict:
        """데이터 업데이트 (폴링 시 호출)."""
        with self._lock:
            self._process_pending_packets()
            self._check_connection_timeout()
            self._elapsed_time += config.ui.poll_interval_ms / 1000
            self._update_chart_data()
            return self._build_state_dict()

    def _process_pending_packets(self) -> None:
        """큐의 패킷들 처리."""
        if not self._packet_queue or not self._parser:
            return

        for raw_data in self._packet_queue.get_all():
            self._process_packet(raw_data)

    def _process_packet(self, raw_data: bytes) -> None:
        """개별 패킷 처리."""
        now = datetime.now()
        self._total_packets += 1

        result = self._parser.parse(raw_data)

        if result.success:
            self._parse_success += 1
        if not result.checksum_ok:
            self._checksum_fail += 1

        # 헤더가 있을 때만 통계 기록 (None 체크 강화)
        if result.success and result.header is not None and self._stats_calc:
            self._stats_calc.record_packet(now, result.header.sequence, len(raw_data))
            self._last_sequence = result.header.sequence

        # 페이로드가 있을 때만 상태 업데이트
        if result.success and result.payload is not None:
            self._update_from_payload(result.payload)

        # 로그 추가 (헤더 None 체크)
        sequence = result.header.sequence if result.header else 0
        msg_code = f"0x{result.header.msg_code:02X}" if result.header else "???"
        
        self._logs_history.appendleft(LogEntry(
            timestamp=now,
            sequence=sequence,
            msg_code=msg_code,
            parse_ok=result.success,
            checksum_ok=result.checksum_ok,
            mode=self._current_mode,
            authority=self._current_authority,
            notes="" if result.success else (result.error or "파싱 실패")
        ))

        self._last_packet_time = now
        self._is_connected = True

    def _update_from_payload(self, payload) -> None:
        """페이로드에서 상태 업데이트."""
        self._current_mode = payload.operation_mode_label
        self._current_authority = payload.authority_label
        self._current_driving = payload.driving_state_label

        # 장치 상태 (constants 모듈 활용)
        self._current_devices = [
            DeviceStatus(
                device_id=did,
                name=name,
                connected=payload.devices.get(name, False),
                error_reason=None if payload.devices.get(name, False) else "연결 안 됨"
            )
            for did, name in zip(DEVICE_IDS, DEVICE_NAMES)
        ]

        # 비상정지 상태
        es = EmergencyStatus()
        es.communication_lost = payload.emergency_status.get("통신 두절", False)
        es.equipment_fail_driving = payload.emergency_status.get("장비고장(주행)", False)
        es.equipment_fail_power = payload.emergency_status.get("장비고장(동력계)", False)
        es.signal_lost_driving = payload.emergency_status.get("신호단절(주행)", False)
        es.signal_lost_autonomous = payload.emergency_status.get("신호단절(자율)", False)
        es.signal_lost_navigation = payload.emergency_status.get("신호단절(항법)", False)
        es.signal_lost_power = payload.emergency_status.get("신호단절(동력계)", False)
        es.signal_lost_comm = payload.emergency_status.get("신호단절(통신)", False)
        es.manual_stop_ocs = payload.emergency_status.get("수동정지(운용통제장치)", False)
        es.manual_stop_near = payload.emergency_status.get("수동정지(근거리조종기)", False)
        self._current_emergency = es

    def _check_connection_timeout(self) -> None:
        """연결 타임아웃 체크."""
        if self._last_packet_time is None:
            return
        elapsed = (datetime.now() - self._last_packet_time).total_seconds()
        if elapsed >= config.ui.down_threshold_sec:
            self._is_connected = False

    def _update_chart_data(self) -> None:
        """차트 데이터 포인트 추가."""
        now = datetime.now()
        stats = self._stats_calc.get_stats_dict() if self._stats_calc else {}
        self._chart_data.append({
            "timestamp": now.strftime("%H:%M:%S"),
            "pps": stats.get("pps", 0),
            "jitter": stats.get("jitter_avg", 0.0),
        })

    def _build_state_dict(self) -> Dict:
        """현재 상태 딕셔너리 생성."""
        stats = self._stats_calc.get_stats_dict() if self._stats_calc else {}
        return {
            "connected": self._is_connected,
            "interface": self._interface,
            "filter": f"{self._src_port}→{self._dst_port}",
            "lastPacketTime": self._last_packet_time.strftime("%H:%M:%S") if self._last_packet_time else "",
            "capturePps": stats.get("pps", 0),
            "filterPass": 100.0,
            "parseSuccess": self._calc_parse_rate(),
            "checksumFail": self._calc_checksum_fail_rate(),
            "packetLoss": stats.get("packet_loss", 0),
            "availability5min": stats.get("availability", 0.0),
            "availability1hour": stats.get("availability", 0.0),
            "jitterP95": stats.get("jitter_p95", 0.0),
            "jitterP99": stats.get("jitter_p99", 0.0),
            "operationalMode": self._current_mode,
            "operationalAuthority": self._current_authority,
            "drivingState": self._current_driving,
            "combinedData": list(self._chart_data),
            "devices": [d.to_dict() for d in self._current_devices],
            "emergencyStatus": self._current_emergency.to_dict(),
            "availabilitySegments": [s.to_dict() for s in self._availability_segments],
        }

    def _calc_parse_rate(self) -> float:
        if self._total_packets == 0:
            return 100.0
        return round((self._parse_success / self._total_packets) * 100, 1)

    def _calc_checksum_fail_rate(self) -> float:
        if self._total_packets == 0:
            return 0.0
        return round((self._checksum_fail / self._total_packets) * 100, 1)

    def get_logs(self, limit: int = 50) -> List[Dict]:
        """로그 목록 반환."""
        with self._lock:
            return [log.to_dict() for log in list(self._logs_history)[:limit]]

    def clear_logs(self) -> None:
        """로그 초기화."""
        with self._lock:
            self._logs_history.clear()

    @property
    def log_count(self) -> int:
        return len(self._logs_history)
