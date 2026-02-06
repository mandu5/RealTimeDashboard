"""
대시보드 데이터 제공자.

PacketStore에서 데이터를 가져와 DashboardData (Dict)로 변환합니다.

책임:
    1. 캡처 시작/중지 제어
    2. PacketProcessor를 통해 패킷 처리
    3. DashboardData (25키) 생성

데이터 흐름:
    PacketProcessor → PacketStore → LiveDataProvider → DashboardData

사용 예시:
    >>> provider = LiveDataProvider(interface="eno2")
    >>> provider.start_capture()
    >>> data = provider.update_data(prev_data)  # DashboardData
    >>> provider.stop_capture()

Note:
    - 캡처 기능은 scapy 패키지가 설치되어 있어야 합니다.
    - Mock 모드에서는 MockDataGenerator를 대신 사용합니다.
"""

import logging
import os
import subprocess
import platform
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional

from ..core import config, DEVICE_NAMES, EmergencyStatus

logger = logging.getLogger(__name__)

try:
    from ..capture import PacketSniffer, PacketQueue, PacketProcessor
    from ..parser import ICDParser
    from .packet_store import PacketStore
    CAPTURE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Capture modules not available: {e}")
    CAPTURE_AVAILABLE = False


class LiveDataProvider:
    """실시간 대시보드 데이터 제공자.
    
    책임:
        - 캡처 제어 (start/stop)
        - DashboardData 생성
    
    데이터 흐름:
        PacketQueue → PacketProcessor → PacketStore → _build_state() → Dict
    """

    def __init__(self, interface: str = None):
        self._interface = interface or os.getenv("UGV_MON_INTERFACE") or config.network.interface
        
        # 양방향 캡처용 포트
        self._vic_port = config.network.vic_port   # 50000
        self._ocs_port = config.network.ocs_port   # 61000
        
        # 현재 캡처 방향
        self._current_direction = "status"
        self._src_port = self._vic_port
        self._dst_port = self._ocs_port
        
        self._lock = Lock()
        
        # 캡처 컴포넌트
        self._sniffer: Optional[PacketSniffer] = None
        self._packet_queue: Optional[PacketQueue] = None
        self._parser: Optional[ICDParser] = None
        self._store: Optional[PacketStore] = None
        self._processor: Optional[PacketProcessor] = None
        
        # 상태
        self._is_connected = False
        self._last_packet_time: Optional[datetime] = None
        self._last_payload = None
        
        # 통계 카운터
        self._total_packets = 0
        self._parse_success = 0
        self._checksum_fail = 0
        
        # 가용성 세그먼트 (회사 방식)
        self._start_time: datetime = datetime.now()
        self._availability_segments: List[Dict] = []
        self._last_avail_change_time: Optional[datetime] = None
        self._last_avail_state: Optional[bool] = None
        
        if CAPTURE_AVAILABLE:
            self._init_modules()

    def _init_modules(self):
        """모듈 초기화."""
        self._packet_queue = PacketQueue(max_size=1000)
        self._parser = ICDParser()
        self._store = PacketStore(window_sec=3600)
        self._processor = PacketProcessor(
            self._packet_queue,
            self._parser,
            self._store
        )

    # =========================================================================
    # 캡처 제어
    # =========================================================================
    
    def start_capture(self) -> bool:
        """캡처 시작."""
        if not CAPTURE_AVAILABLE:
            return False
        if self._sniffer:
            self._cleanup_sniffer()
        try:
            self._sniffer = PacketSniffer(
                self._interface, 
                self._src_port, 
                self._dst_port, 
                self._packet_queue.put
            )
            self._sniffer.start()
            self._is_connected = True
            logger.info(f"Capture started on: {self._interface} ({self._src_port}→{self._dst_port})")
            return True
        except (PermissionError, OSError) as e:
            logger.error(f"Capture failed: {e}")
            return False

    def stop_capture(self):
        """캡처 중지."""
        self._cleanup_sniffer()
        self._is_connected = False

    def _cleanup_sniffer(self):
        """스니퍼 정리."""
        if self._sniffer:
            try:
                if self._sniffer.is_running():
                    self._sniffer.stop()
            except Exception:
                pass
            self._sniffer = None

    def switch_interface(self, new_interface: str) -> bool:
        """인터페이스 전환."""
        with self._lock:
            if new_interface == self._interface:
                return True
            was_running = self._is_connected
            if was_running:
                self.stop_capture()
            
            # 스트림 상태 리셋 (지터 오염 방지)
            if self._store:
                self._store.reset_stream_state()
            
            old = self._interface
            self._interface = new_interface
            if was_running:
                if not self.start_capture():
                    self._interface = old
                    self.start_capture()
                    return False
            return True

    def toggle_connection(self) -> bool:
        """연결 토글."""
        with self._lock:
            if self._is_connected:
                self.stop_capture()
                if self._store:
                    self._store.reset_stream_state()
                return False
            
            if self._store:
                self._store.reset_stream_state()
            return self.start_capture()

    def toggle_direction(self) -> str:
        """캡처 방향 전환."""
        with self._lock:
            if self._sniffer:
                self.stop_capture()
            
            # 방향 전환
            if self._current_direction == "status":
                self._current_direction = "control"
                self._src_port = self._ocs_port
                self._dst_port = self._vic_port
            else:
                self._current_direction = "status"
                self._src_port = self._vic_port
                self._dst_port = self._ocs_port
            
            logger.info(f"Direction changed: {self._current_direction} ({self._src_port}→{self._dst_port})")
            
            # 스트림 상태 초기화
            if self._store:
                self._store.reset()
            
            # 통계 초기화
            self._total_packets = 0
            self._parse_success = 0
            self._checksum_fail = 0
            
            if self._is_connected:
                self.start_capture()
            
            return self._current_direction

    @property
    def current_direction(self) -> str:
        """현재 캡처 방향."""
        return self._current_direction

    def get_available_interfaces(self) -> List[str]:
        """사용 가능한 인터페이스 목록."""
        try:
            if platform.system() == "Linux":
                result = subprocess.run(
                    ["ip", "link", "show"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                interfaces = []
                for line in result.stdout.split("\n"):
                    if ": " in line and "@" not in line.split(": ")[1]:
                        interfaces.append(line.split(": ")[1].split("@")[0])
                return interfaces or ["lo", "eth0"]
            elif platform.system() == "Darwin":
                result = subprocess.run(
                    ["networksetup", "-listallhardwareports"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                interfaces = ["lo0"]
                for line in result.stdout.split("\n"):
                    if line.startswith("Device:"):
                        interfaces.append(line.replace("Device:", "").strip())
                return interfaces
            return ["lo", "eth0"]
        except Exception:
            return ["lo", "eno2", "eno3"]

    # =========================================================================
    # 데이터 생성/업데이트
    # =========================================================================
    
    def generate_initial_data(self) -> Dict:
        """초기 대시보드 데이터 생성."""
        return self._build_state()

    def update_data(self, prev_data: Dict) -> Dict:
        """데이터 업데이트."""
        with self._lock:
            # 패킷 처리 (packet_processor 사용)
            if self._processor:
                result = self._processor.process_pending()
                self._total_packets += result.count
                self._parse_success += result.success_count
                self._checksum_fail += result.checksum_fail_count
                
                if result.last_payload:
                    self._last_payload = result.last_payload
                
                if result.count > 0:
                    self._last_packet_time = datetime.now()
            
            # 타임아웃 체크
            self._check_timeout()
            
            # 가용성 상태 기록
            self._record_availability_change(self._is_connected)
            
            # 연결 상태 기록
            if self._store:
                self._store.record_connection_change(self._is_connected)
            
            return self._build_state()

    def _check_timeout(self):
        """타임아웃 체크."""
        if self._last_packet_time:
            elapsed = (datetime.now() - self._last_packet_time).total_seconds()
            if elapsed >= config.ui.down_threshold_sec:
                self._is_connected = False

    # =========================================================================
    # 가용성 세그먼트 (회사 방식)
    # =========================================================================
    
    def _record_availability_change(self, new_is_up: bool) -> None:
        """연결 상태 변화 시 가용성 세그먼트 기록."""
        now = datetime.now()

        if self._last_avail_change_time is None:
            self._last_avail_change_time = now
            self._last_avail_state = new_is_up
            return

        if new_is_up == self._last_avail_state:
            return

        start_sec = (self._last_avail_change_time - self._start_time).total_seconds()
        end_sec = (now - self._start_time).total_seconds()
        
        self._availability_segments.append({
            "start": max(0, start_sec),
            "end": max(0, end_sec),
            "isUp": self._last_avail_state,
        })

        self._last_avail_change_time = now
        self._last_avail_state = new_is_up
        self._trim_availability_segments(max_sec=3600)

    def _trim_availability_segments(self, max_sec: int = 3600) -> None:
        """오래된 세그먼트 제거."""
        now = datetime.now()
        cutoff = (now - self._start_time).total_seconds() - max_sec
        self._availability_segments = [
            seg for seg in self._availability_segments if seg["end"] > cutoff
        ]

    def _build_availability_segments(self) -> List[Dict]:
        """가용성 세그먼트 반환."""
        timeline_sec = config.ui.timeline_duration_sec
        now = datetime.now()
        current_offset = (now - self._start_time).total_seconds()
        
        if not self._availability_segments:
            return [{"start": 0, "end": timeline_sec, "isUp": self._is_connected}]
        
        normalized = []
        for seg in self._availability_segments:
            start_pos = timeline_sec - (current_offset - seg["start"])
            end_pos = timeline_sec - (current_offset - seg["end"])
            
            if end_pos < 0 or start_pos > timeline_sec:
                continue
            
            normalized.append({
                "start": max(0, start_pos),
                "end": min(timeline_sec, end_pos),
                "isUp": seg["isUp"],
            })
        
        if self._last_avail_change_time:
            last_start = timeline_sec - (
                current_offset - 
                (self._last_avail_change_time - self._start_time).total_seconds()
            )
            if last_start < timeline_sec:
                normalized.append({
                    "start": max(0, last_start),
                    "end": timeline_sec,
                    "isUp": self._last_avail_state if self._last_avail_state is not None else self._is_connected,
                })
        
        return normalized if normalized else [{"start": 0, "end": timeline_sec, "isUp": self._is_connected}]

    # =========================================================================
    # 상태 빌드 (DashboardData 생성)
    # =========================================================================

    def _build_state(self) -> Dict:
        """전체 대시보드 상태 빌드 (25키)."""
        return {
            **self._build_connection_state(),
            **self._build_stats_state(),
            **self._build_operational_state(),
            **self._build_ui_state(),
        }

    def _build_connection_state(self) -> Dict:
        """연결 상태 (5키)."""
        return {
            "connected": self._is_connected,
            "interface": self._interface,
            "direction": self._current_direction,
            "filter": f"{self._src_port}→{self._dst_port}",
            "lastPacketTime": self._last_packet_time.strftime("%H:%M:%S") if self._last_packet_time else "",
        }

    def _build_stats_state(self) -> Dict:
        """통계 상태 (9키)."""
        if self._store:
            stats = self._store.get_stats_dict()
            hourly_avail = self._store.get_hourly_availability()
        else:
            stats = {}
            hourly_avail = 0.0
        
        return {
            "capturePps": stats.get("pps", 0),
            "parseSuccess": round((self._parse_success / max(self._total_packets, 1)) * 100, 1),
            "checksumFail": round((self._checksum_fail / max(self._total_packets, 1)) * 100, 1),
            "packetLoss": stats.get("packet_loss", 0),
            "availability": stats.get("availability", 0.0),
            "availabilityHourly": hourly_avail,
            "jitterCurrent": stats.get("jitter_current", 0.0),
            "jitterP95": stats.get("jitter_p95", 0.0),
            "jitterP99": stats.get("jitter_p99", 0.0),
        }

    def _build_operational_state(self) -> Dict:
        """운용 상태 (4키)."""
        if self._last_payload:
            p = self._last_payload
            return {
                "operationalMode": p.operation_mode,
                "operationalAuthority": p.authority,
                "drivingState": p.driving_state,
                "emergencyStatus": p.get_emergency_dict(),
            }
        return {
            "operationalMode": "--- (대기 중)",
            "operationalAuthority": "--- (대기 중)",
            "drivingState": "--- (대기 중)",
            "emergencyStatus": EmergencyStatus().to_dict(),
        }

    def _build_ui_state(self) -> Dict:
        """UI 상태 (7키)."""
        # 장치 상태
        if self._last_payload:
            devices = [
                {"name": name, "connected": self._last_payload.devices.get(name, False)}
                for name in DEVICE_NAMES
            ]
        else:
            devices = [{"name": n, "connected": False} for n in DEVICE_NAMES]
        
        # 저장소에서 데이터 가져오기
        if self._store:
            chart_data = self._store.get_chart_data(limit=180)
            msg_code_stats = self._store.get_stats_by_code()
            connection_history = self._store.get_connection_history(limit=10)
            mode_transitions = self._store.get_mode_transitions(limit=10)
            emergency_counts = self._store.get_emergency_counts()
        else:
            chart_data = []
            msg_code_stats = {}
            connection_history = []
            mode_transitions = []
            emergency_counts = {}
        
        return {
            "combinedData": chart_data,
            "devices": devices,
            "availabilitySegments": self._build_availability_segments(),
            "msgCodeStats": msg_code_stats,
            "connectionHistory": connection_history,
            "modeTransitions": mode_transitions,
            "emergencyCounts": emergency_counts,
        }

    # =========================================================================
    # 로그 관련
    # =========================================================================
    
    def get_logs(self, limit: int = 50) -> List[Dict]:
        """로그 목록 반환."""
        with self._lock:
            if self._store:
                return self._store.get_logs(limit=limit)
            return []

    def clear_logs(self):
        """로그 초기화."""
        with self._lock:
            if self._store:
                self._store.reset()

    @property
    def log_count(self) -> int:
        """로그 수."""
        if self._store:
            return self._store.record_count
        return 0
