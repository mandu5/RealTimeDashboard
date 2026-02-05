"""
실시간 패킷 캡처 및 분석 - 대시보드 데이터 제공.

이 모듈은 VIC-OCS 통신 패킷을 실시간으로 캡처하고 분석하여
대시보드에 표시할 데이터를 제공합니다.

주요 기능:
    - 네트워크 인터페이스에서 UDP 패킷 캡처 (scapy)
    - ICD 헤더/페이로드 파싱
    - 통신 품질 통계 계산 (PPS, 지터, 손실률)
    - 가용성 세그먼트 추적
    - 운용 상태 이력 관리 (Phase 4-6)

사용 예시:
    >>> provider = LiveDataProvider(interface="eno2")
    >>> provider.start_capture()
    >>> data = provider.update_data(prev_data)
    >>> provider.stop_capture()

Note:
    캡처 기능은 scapy 패키지가 설치되어 있어야 합니다.
    Mock 모드에서는 MockDataGenerator를 대신 사용합니다.
"""

import logging
import os
import subprocess
import platform
from collections import deque
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional

from ..core import config, DEVICE_NAMES, LogEntry, EmergencyStatus

logger = logging.getLogger(__name__)

try:
    from ..capture import PacketSniffer, PacketQueue
    from ..parser import ICDParser
    from ..analysis import StatsCalculator
    CAPTURE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Capture modules not available: {e}")
    CAPTURE_AVAILABLE = False


class LiveDataProvider:
    """실시간 데이터 제공자 (헤더 기반).
    
    4주차 금요일 추가: 양방향 캡처 (상태/제어 메시지 전환)
    """

    def __init__(self, interface: str = None):
        self._interface = interface or os.getenv("UGV_MON_INTERFACE") or config.network.interface
        
        # 양방향 캡처용 포트 (4주차 금요일 추가)
        self._vic_port = config.network.vic_port   # 50000
        self._ocs_port = config.network.ocs_port   # 61000
        
        # 현재 캡처 방향 ("status" or "control")
        self._current_direction = "status"
        self._src_port = self._vic_port  # 기본: 50000 (상태)
        self._dst_port = self._ocs_port  # 기본: 61000
        
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
        self._last_payload = None
        
        # 가용성 세그먼트 (회사 방식)
        self._start_time: datetime = datetime.now()
        self._availability_segments: List[Dict] = []
        self._last_avail_change_time: Optional[datetime] = None
        self._last_avail_state: Optional[bool] = None
        
        # Phase 4: 연결 이력
        self._connection_history: deque = deque(maxlen=100)
        self._last_connection_state: Optional[bool] = None
        
        # Phase 5: 운용상태 전이 이력
        self._mode_transitions: deque = deque(maxlen=50)
        self._last_op_mode: Optional[str] = None
        
        # Phase 6: 비상정지 원인 통계
        self._emergency_counts: Dict[str, int] = {}
        
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
            logger.info(f"Capture started on: {self._interface} ({self._src_port}→{self._dst_port})")
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
            
            # 인터페이스 전환 시 스트림 상태 리셋 (5주차: 지터 오염 방지)
            if self._stats_calc:
                self._stats_calc.reset_stream_state(clear_records=False)
            
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
                # 연결 해제 시 스트림 상태 리셋 (5주차: 지터 오염 방지)
                if self._stats_calc:
                    self._stats_calc.reset_stream_state(clear_records=False)
                return False
            
            # 연결 시작 시 스트림 상태 리셋 (5주차: 지터 오염 방지)
            if self._stats_calc:
                self._stats_calc.reset_stream_state(clear_records=False)
            return self.start_capture()

    def toggle_direction(self) -> str:
        """캡처 방향 전환 (상태 ↔ 제어 메시지).
        
        Returns:
            새로운 방향 ("status" or "control")
        """
        with self._lock:
            # 현재 캡처 중지
            if self._sniffer:
                self.stop_capture()
            
            # 방향 전환
            if self._current_direction == "status":
                self._current_direction = "control"
                self._src_port = self._ocs_port  # 61000
                self._dst_port = self._vic_port  # 50000
            else:
                self._current_direction = "status"
                self._src_port = self._vic_port  # 50000
                self._dst_port = self._ocs_port  # 61000
            
            logger.info(f"Direction changed: {self._current_direction} ({self._src_port}→{self._dst_port})")
            
            # 통계 스트림 상태 초기화 (5주차 월요일: reset_stream_state 사용)
            if self._stats_calc:
                self._stats_calc.reset_stream_state(clear_records=True)
            
            # 기존 연결 상태였으면 다시 시작
            if self._is_connected:
                self.start_capture()
            
            return self._current_direction

    @property
    def current_direction(self) -> str:
        """현재 캡처 방향 반환."""
        return self._current_direction

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
        """초기 대시보드 데이터 생성."""
        return self._build_state() 

    def update_data(self, prev_data: Dict) -> Dict:
        """패킷 처리 및 데이터 업데이트."""
        with self._lock:
            self._process_packets()
            self._check_timeout()
            self._update_chart()
            # 가용성 상태 변경 기록 (회사 방식)
            self._record_availability_change(self._is_connected)
            return self._build_state()

    def _process_packets(self):
        if not self._packet_queue or not self._parser:
            return
        for capture_time, raw in self._packet_queue.get_all():
            self._process_packet(raw, capture_time)

    def _process_packet(self, raw: bytes, capture_time: datetime):
        """패킷 처리 (캡처 시점 timestamp 사용)."""
        self._total_packets += 1
        result = self._parser.parse(raw)
        
        if result.success:
            self._parse_success += 1
        if not result.checksum_ok:
            self._checksum_fail += 1
        
        # 헤더 기반 통계 (msg_code 포함)
        if result.success and result.header and self._stats_calc:
            self._stats_calc.record_packet(
                capture_time,
                result.header.sequence,
                len(raw),
                result.header.msg_code  # msg_code 추가
            )
        
        # 페이로드 저장 및 이력 업데이트
        if result.payload:
            self._update_histories(result.payload)
            self._last_payload = result.payload
        
        # 로그 추가 (헤더 + 페이로드 정보)
        seq = result.header.sequence if result.header else 0
        msg = f"0x{result.header.msg_code:02X}" if result.header else "???"
        
        # 페이로드에서 운용 정보 추출
        mode = "---"
        authority = "---"
        if result.payload:
            mode = result.payload.operation_mode
            authority = result.payload.authority
        
        self._logs.appendleft(LogEntry(
            capture_time, seq, msg, result.success, result.checksum_ok,
            mode, authority,
            "" if result.success else (result.error or "파싱 실패")
        ))
        self._last_packet_time = capture_time
        # NOTE: self._is_connected는 toggle_connection()에서만 제어
        # 패킷 수신 시 덮어쓰지 않음 (버튼 즉시 반응 문제 해결)

    def _check_timeout(self):
        if self._last_packet_time and (datetime.now() - self._last_packet_time).total_seconds() >= config.ui.down_threshold_sec:
            self._is_connected = False

    def _update_chart(self):
        now = datetime.now()
        stats = self._stats_calc.get_stats_dict() if self._stats_calc else {}
        jitter = stats.get("jitter_current", 0.0)
        
        # 5주차: 지터 필터링 (200ms 이상은 0으로 표시)
        from ..analysis.stats_calculator import MAX_JITTER_MS
        if jitter > MAX_JITTER_MS:
            jitter = 0.0
        
        self._chart_data.append({
            "timestamp": now.strftime("%H:%M:%S"), 
            "pps": stats.get("pps", 0), 
            "jitter": jitter
        })

    def _update_histories(self, payload):
        """Phase 4-6: 페이로드 기반 이력 업데이트."""
        now = datetime.now()
        
        # Phase 4: 연결 상태 변경 이력
        if self._last_connection_state != self._is_connected:
            self._connection_history.append({
                "timestamp": now.isoformat(),
                "connected": self._is_connected,
                "duration": None,  # 다음 변경 시 계산
            })
            # 이전 항목에 duration 계산
            if len(self._connection_history) >= 2:
                prev = self._connection_history[-2]
                if prev.get("duration") is None:
                    duration = (now - datetime.fromisoformat(prev["timestamp"])).total_seconds()
                    prev["duration"] = round(duration, 1)
            self._last_connection_state = self._is_connected
        
        # Phase 5: 운용모드 전이 이력
        current_mode = payload.operation_mode
        if self._last_op_mode and self._last_op_mode != current_mode:
            self._mode_transitions.append({
                "timestamp": now.isoformat(),
                "from": self._last_op_mode,
                "to": current_mode,
            })
        self._last_op_mode = current_mode
        
        # Phase 6: 비상정지 원인 집계
        if payload.is_emergency:
            reasons = payload.get_emergency_reasons()
            for reason in reasons:
                self._emergency_counts[reason] = self._emergency_counts.get(reason, 0) + 1

    def _record_availability_change(self, new_is_up: bool) -> None:
        """연결 상태 변화 시 가용성 세그먼트 기록 (회사 방식).
        
        - 이전 상태 구간을 닫고 (END 확정)
        - 새 상태 시작 시각을 저장
        """
        now = datetime.now()

        # 최초 호출 (세그먼트 시작점만 세팅)
        if self._last_avail_change_time is None:
            self._last_avail_change_time = now
            self._last_avail_state = new_is_up
            return

        # 상태가 바뀌지 않았으면 기록할 필요 없음
        if new_is_up == self._last_avail_state:
            return

        # 이전 상태 구간을 세그먼트로 확정
        start_sec = (self._last_avail_change_time - self._start_time).total_seconds()
        end_sec = (now - self._start_time).total_seconds()
        
        self._availability_segments.append({
            "start": max(0, start_sec),
            "end": max(0, end_sec),
            "isUp": self._last_avail_state,
        })

        # 새 상태 시작점 갱신
        self._last_avail_change_time = now
        self._last_avail_state = new_is_up
        
        # 오래된 세그먼트 정리 (1시간 초과)
        self._trim_availability_segments(max_sec=3600)

    def _trim_availability_segments(self, max_sec: int = 3600) -> None:
        """오래된 세그먼트 제거."""
        now = datetime.now()
        cutoff = (now - self._start_time).total_seconds() - max_sec
        self._availability_segments = [
            seg for seg in self._availability_segments if seg["end"] > cutoff
        ]

    def _build_availability_segments(self) -> List[Dict]:
        """가용성 세그먼트 반환 (회사 방식).
        
        타임라인 범위로 정규화하여 반환.
        """
        timeline_sec = config.ui.timeline_duration_sec
        now = datetime.now()
        current_offset = (now - self._start_time).total_seconds()
        
        if not self._availability_segments:
            # 세그먼트 없으면 현재 상태로 전체 표시
            return [{"start": 0, "end": timeline_sec, "isUp": self._is_connected}]
        
        # 세그먼트를 0~timeline_sec 범위로 정규화
        normalized = []
        for seg in self._availability_segments:
            # 상대 위치 계산 (현재 시점 기준 과거)
            start_pos = timeline_sec - (current_offset - seg["start"])
            end_pos = timeline_sec - (current_offset - seg["end"])
            
            # 범위 체크
            if end_pos < 0 or start_pos > timeline_sec:
                continue
            
            normalized.append({
                "start": max(0, start_pos),
                "end": min(timeline_sec, end_pos),
                "isUp": seg["isUp"],
            })
        
        # 현재 진행 중인 세그먼트 추가
        if self._last_avail_change_time:
            last_start = timeline_sec - (current_offset - (self._last_avail_change_time - self._start_time).total_seconds())
            if last_start < timeline_sec:
                normalized.append({
                    "start": max(0, last_start),
                    "end": timeline_sec,
                    "isUp": self._last_avail_state if self._last_avail_state is not None else self._is_connected,
                })
        
        return normalized if normalized else [{"start": 0, "end": timeline_sec, "isUp": self._is_connected}]

    # =========================================================================
    # 상태 빌드 (리팩토링됨)
    # =========================================================================

    def _build_state(self) -> Dict:
        """전체 대시보드 상태 빌드."""
        return {
            **self._build_connection_state(),
            **self._build_stats_state(),
            **self._build_operational_state(),
            **self._build_ui_state(),
        }

    def _build_connection_state(self) -> Dict:
        """연결 상태 관련 필드."""
        return {
            "connected": self._is_connected,
            "interface": self._interface,
            "direction": self._current_direction,
            "filter": f"{self._src_port}→{self._dst_port}",
            "lastPacketTime": self._last_packet_time.strftime("%H:%M:%S") if self._last_packet_time else "",
        }

    def _build_stats_state(self) -> Dict:
        """통계 관련 필드."""
        stats = self._stats_calc.get_stats_dict() if self._stats_calc else {}
        hourly_avail = self._stats_calc.get_hourly_availability() if self._stats_calc else 0.0
        return {
            "capturePps": stats.get("pps", 0),
            "parseSuccess": round((self._parse_success / max(self._total_packets, 1)) * 100, 1),
            "checksumFail": round((self._checksum_fail / max(self._total_packets, 1)) * 100, 1),
            "packetLoss": stats.get("packet_loss", 0),
            "availability5min": stats.get("availability", 0.0),
            "availability": stats.get("availability", 0.0),  # Phase 2: UI용
            "availabilityHourly": hourly_avail,  # Phase 2: 1시간 가용성
            "jitterCurrent": stats.get("jitter_current", 0.0),
            "jitterP95": stats.get("jitter_p95", 0.0),
            "jitterP99": stats.get("jitter_p99", 0.0),
        }

    def _build_operational_state(self) -> Dict:
        """운용 상태 필드 (페이로드 기반)."""
        if self._last_payload:
            p = self._last_payload
            return {
                "operationalMode": p.operation_mode,
                "operationalAuthority": p.authority,
                "drivingState": p.driving_state,
                "emergencyStatus": p.get_emergency_dict(),  # UI용 딕셔너리 사용
            }
        else:
            return {
                "operationalMode": "--- (대기 중)",
                "operationalAuthority": "--- (대기 중)",
                "drivingState": "--- (대기 중)",
                "emergencyStatus": EmergencyStatus().to_dict(),
            }

    def _build_ui_state(self) -> Dict:
        """UI 렌더링용 필드."""
        # 페이로드에서 장치 상태 추출
        if self._last_payload:
            payload_devices = [
                {"name": name, "connected": self._last_payload.devices.get(name, False)}
                for name in DEVICE_NAMES
            ]
        else:
            payload_devices = [{"name": n, "connected": False} for n in DEVICE_NAMES]
        
        # msg_code별 통계 (Phase 3)
        msg_code_stats = self._stats_calc.get_stats_by_code() if self._stats_calc else {}
        
        return {
            "combinedData": list(self._chart_data),
            "devices": payload_devices,
            "availabilitySegments": self._build_availability_segments(),
            "msgCodeStats": msg_code_stats,
            # Phase 4-6: 이력 데이터
            "connectionHistory": list(self._connection_history)[-10:],  # 최근 10개
            "modeTransitions": list(self._mode_transitions)[-10:],
            "emergencyCounts": dict(self._emergency_counts),
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
