"""
Live Data Provider Module.

실시간 패킷 캡처와 ICD 파싱을 통합하여
대시보드 UI에 데이터를 제공합니다.

=============================================================================
데이터 흐름:
1. PacketSniffer가 UDP 패킷 캡처 (별도 스레드)
2. 캡처된 패킷을 PacketQueue에 저장
3. UI 폴링 시 큐에서 패킷을 꺼내 ICDParser로 파싱
4. 파싱 결과를 기반으로 대시보드 상태 업데이트
5. StatsCalculator로 통계 계산
6. AnomalyDetector로 이상 탐지

MockDataGenerator와 동일한 인터페이스를 제공하여
개발 중에는 Mock, 실제 환경에서는 Live로 전환 가능합니다.

환경변수:
- UGV_MON_USE_LIVE=true: Live 모드 활성화
- UGV_MON_INTERFACE: 캡처 인터페이스 (기본: lo)

Q: 왜 MockDataGenerator와 동일한 인터페이스인가요?
A: 다형성(Polymorphism) 활용. 코드 변경 없이 데이터 소스 전환 가능.
   테스트 시 Mock, 운영 시 Live로 쉽게 전환합니다.
=============================================================================
"""

import logging
import os
from collections import deque
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional

from ..config import config
from .models import (
    DashboardState,
    LogEntry,
    DeviceStatus,
    AvailabilitySegment,
    EmergencyStatus,
)

# 로거 설정
logger = logging.getLogger(__name__)

# 캡처/파서/분석 모듈 임포트 (선택적)
try:
    from ..capture import PacketSniffer, PacketQueue, CaptureStats
    from ..parser import ICDParser, ParseResult
    from ..analysis import StatsCalculator, AnomalyDetector
    CAPTURE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Capture/Parser modules not available: {e}")
    CAPTURE_AVAILABLE = False


class LiveDataProvider:
    """
    실시간 데이터 제공자.
    
    PacketSniffer와 ICDParser를 연결하여 대시보드에
    실시간 데이터를 제공합니다.
    
    MockDataGenerator와 동일한 메서드 시그니처를 제공하여
    코드 변경 없이 데이터 소스를 전환할 수 있습니다.
    
    Attributes:
        interface: 캡처 인터페이스
        src_port: VIC 송신 포트
        dst_port: OCS 수신 포트
    
    사용 예시:
        provider = LiveDataProvider(interface="lo")
        provider.start_capture()
        
        # 폴링 시마다 호출 (MockDataGenerator와 동일)
        data = provider.update_data(prev_data)
        logs = provider.get_logs()
        
        provider.stop_capture()
    """
    
    def __init__(
        self,
        interface: str = None,
        src_port: int = None,
        dst_port: int = None
    ):
        """
        LiveDataProvider 초기화.
        
        Args:
            interface: 캡처 인터페이스 (기본값: config에서 로드)
            src_port: 송신 포트 (기본값: config에서 로드)
            dst_port: 수신 포트 (기본값: config에서 로드)
        
        Q: 왜 기본값이 None인가요?
        A: None이면 config에서 값을 읽습니다.
           테스트 시에는 직접 값을 지정할 수 있습니다.
        """
        # 설정 로드 (인자 > 환경변수 > config 기본값)
        self._interface = interface or os.getenv("UGV_MON_INTERFACE") or config.network.interface
        self._src_port = src_port or config.network.source_port
        self._dst_port = dst_port or config.network.dest_port
        
        # =====================================================================
        # 캡처 관련 컴포넌트
        # =====================================================================
        self._packet_queue: Optional[PacketQueue] = None
        self._sniffer: Optional[PacketSniffer] = None
        self._parser: Optional[ICDParser] = None
        
        # =====================================================================
        # 분석 모듈
        # =====================================================================
        self._stats_calc: Optional[StatsCalculator] = None
        self._anomaly_detector: Optional[AnomalyDetector] = None
        
        # =====================================================================
        # 상태 저장소
        # =====================================================================
        self._logs_history: deque = deque(maxlen=config.ui.max_log_entries)
        self._chart_data: deque = deque(maxlen=config.ui.max_chart_points)
        self._availability_segments: List[AvailabilitySegment] = []
        
        # 현재 상태
        self._is_connected = False
        self._last_packet_time: Optional[datetime] = None
        self._last_sequence: Optional[int] = None
        
        # 현재 운용 상태 (파싱 결과에서 업데이트)
        self._current_operation_mode = "준비 (PREP)"
        self._current_authority = "해제됨 (RELEASED)"
        self._current_driving_state = "원격 (REMOTE)"
        self._current_devices: List[DeviceStatus] = []
        self._current_emergency = EmergencyStatus()
        
        # 통계
        self._total_packets = 0
        self._parse_success = 0
        self._checksum_fail = 0
        
        # 타임라인 관리
        self._elapsed_time = 0.0
        
        # 스레드 안전성
        self._lock = Lock()
        
        # 모듈 초기화
        if CAPTURE_AVAILABLE:
            self._init_modules()
        else:
            logger.warning("Capture modules not available - using degraded mode")
    
    def _init_modules(self) -> None:
        """캡처/파서/분석 모듈 초기화."""
        self._packet_queue = PacketQueue(max_size=1000)
        self._parser = ICDParser()
        self._stats_calc = StatsCalculator(window_sec=60)
        self._anomaly_detector = AnomalyDetector()
        
        logger.info(
            f"LiveDataProvider initialized: "
            f"interface={self._interface}, "
            f"filter={self._src_port}→{self._dst_port}"
        )
    
    def start_capture(self) -> bool:
        """
        패킷 캡처 시작.
        
        Returns:
            성공 여부
        
        Note:
            - root 권한이 필요합니다
            - 실패해도 예외를 던지지 않고 False 반환
        """
        if not CAPTURE_AVAILABLE:
            logger.error("Capture modules not available")
            return False
        
        if self._sniffer and self._sniffer.is_running():
            logger.warning("Sniffer is already running")
            return True
        
        try:
            self._sniffer = PacketSniffer(
                interface=self._interface,
                src_port=self._src_port,
                dst_port=self._dst_port,
                callback=self._packet_queue.put
            )
            self._sniffer.start()
            self._is_connected = True
            logger.info("Capture started successfully")
            return True
            
        except PermissionError:
            logger.error(
                "Permission denied. Solutions:\n"
                "  1. Run with sudo: sudo python run.py\n"
                "  2. Set capability: sudo setcap cap_net_raw+ep $(which python3)"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to start capture: {e}")
            return False
    
    def stop_capture(self) -> None:
        """패킷 캡처 중지."""
        if self._sniffer:
            self._sniffer.stop()
            self._is_connected = False
            logger.info("Capture stopped")
    
    def is_capturing(self) -> bool:
        """캡처 실행 중인지 확인."""
        return self._sniffer is not None and self._sniffer.is_running()
    
    def generate_initial_data(self) -> Dict:
        """
        초기 대시보드 데이터 생성.
        
        MockDataGenerator.generate_initial_data()와 동일한 시그니처.
        캡처 시작 전에 호출됩니다.
        
        Returns:
            대시보드 상태 딕셔너리
        """
        now = datetime.now()
        
        # 초기 장치 상태 (모두 미연결)
        self._current_devices = [
            DeviceStatus("vic", "VIC", connected=False),
            DeviceStatus("rdc", "RDC", connected=False),
            DeviceStatus("adc", "ADC", connected=False),
            DeviceStatus("fcam", "FCAM", connected=False),
            DeviceStatus("rcam", "RCAM", connected=False),
            DeviceStatus("acam", "ACAM", connected=False),
            DeviceStatus("scs", "SCS", connected=False),
            DeviceStatus("dip", "DIP", connected=False),
            DeviceStatus("tcc", "TCC", connected=False),
            DeviceStatus("tm", "TM", connected=False),
        ]
        
        # 초기 가용성 세그먼트 (전체 down)
        self._availability_segments = [
            AvailabilitySegment(
                start_sec=0,
                end_sec=config.ui.timeline_duration_sec,
                is_up=False
            )
        ]
        
        return {
            "connected": self._is_connected,
            "interface": self._interface,
            "filter": f"{self._src_port}→{self._dst_port}",
            "lastPacketTime": "",
            "capturePps": 0,
            "filterPass": 100.0,
            "parseSuccess": 100.0,
            "checksumFail": 0.0,
            "packetLoss": 0,
            "availability5min": 0.0,
            "availability1hour": 0.0,
            "jitterP95": 0.0,
            "jitterP99": 0.0,
            "operationalMode": self._current_operation_mode,
            "operationalAuthority": self._current_authority,
            "drivingState": self._current_driving_state,
            "combinedData": list(self._chart_data),
            "devices": [d.to_dict() for d in self._current_devices],
            "emergencyStatus": self._current_emergency.to_dict(),
            "availabilitySegments": [s.to_dict() for s in self._availability_segments],
        }
    
    def update_data(self, prev_data: Dict) -> Dict:
        """
        대시보드 데이터 업데이트.
        
        MockDataGenerator.update_data()와 동일한 시그니처.
        UI 폴링 시마다 호출됩니다.
        
        Args:
            prev_data: 이전 상태 딕셔너리
        
        Returns:
            업데이트된 상태 딕셔너리
        """
        with self._lock:
            # 큐에서 패킷 가져와서 처리
            self._process_pending_packets()
            
            # 연결 타임아웃 체크
            self._check_connection_timeout()
            
            # 타임라인 업데이트
            self._elapsed_time += config.ui.poll_interval_ms / 1000
            self._update_availability_timeline()
            
            # 통계 계산
            stats = self._get_current_stats()
            
            # 새 차트 데이터 포인트 추가
            now = datetime.now()
            new_point = {
                "timestamp": now.strftime("%H:%M:%S"),
                "pps": stats.get("pps", 0),
                "jitter": stats.get("jitter_avg", 0.0),
            }
            self._chart_data.append(new_point)
            
            return {
                **prev_data,
                "connected": self._is_connected,
                "lastPacketTime": (
                    self._last_packet_time.strftime("%H:%M:%S")
                    if self._last_packet_time else ""
                ),
                "capturePps": stats.get("pps", 0),
                "filterPass": 100.0,  # BPF 필터 통과율
                "parseSuccess": self._calc_parse_success_rate(),
                "checksumFail": self._calc_checksum_fail_rate(),
                "packetLoss": stats.get("packet_loss", 0),
                "availability5min": self._calc_availability(300),
                "availability1hour": self._calc_availability(3600),
                "jitterP95": stats.get("jitter_p95", 0.0),
                "jitterP99": stats.get("jitter_p99", 0.0),
                "operationalMode": self._current_operation_mode,
                "operationalAuthority": self._current_authority,
                "drivingState": self._current_driving_state,
                "combinedData": list(self._chart_data),
                "devices": [d.to_dict() for d in self._current_devices],
                "emergencyStatus": self._current_emergency.to_dict(),
                "availabilitySegments": [s.to_dict() for s in self._availability_segments],
            }
    
    def _process_pending_packets(self) -> None:
        """큐에 있는 모든 패킷 처리."""
        if not self._packet_queue or not self._parser:
            return
        
        packets = self._packet_queue.get_all()
        
        for raw_data in packets:
            self._process_single_packet(raw_data)
    
    def _process_single_packet(self, raw_data: bytes) -> None:
        """
        개별 패킷 처리.
        
        Args:
            raw_data: 원시 패킷 데이터
        """
        now = datetime.now()
        self._total_packets += 1
        
        # 파싱
        result = self._parser.parse(raw_data)
        
        # 파싱 통계 업데이트
        if result.success:
            self._parse_success += 1
        if not result.checksum_ok:
            self._checksum_fail += 1
        
        # 통계 기록 (StatsCalculator)
        if result.success and result.header and self._stats_calc:
            jitter = self._stats_calc.record_packet(
                timestamp=now,
                sequence=result.header.sequence,
                size=len(raw_data)
            )
            
            # 이상 탐지
            if self._anomaly_detector and jitter is not None:
                self._anomaly_detector.check_jitter(jitter)
            
            # 시퀀스 갭 체크 (패킷 손실)
            if self._anomaly_detector and self._last_sequence is not None:
                self._anomaly_detector.check_packet_loss(
                    self._last_sequence,
                    result.header.sequence
                )
            
            self._last_sequence = result.header.sequence
        
        # 상태 업데이트
        if result.success and result.payload:
            self._update_state_from_payload(result.payload)
        
        # 로그 추가
        self._add_log_entry(result, now)
        
        # 연결 상태 업데이트
        self._last_packet_time = now
        self._is_connected = True
    
    def _update_state_from_payload(self, payload) -> None:
        """
        페이로드에서 상태 업데이트.
        
        Args:
            payload: StatusPayload 객체
        """
        # 운용 상태
        self._current_operation_mode = payload.operation_mode_label
        self._current_authority = payload.authority_label
        self._current_driving_state = payload.driving_state_label
        
        # 장치 상태
        device_names = ["VIC", "RDC", "ADC", "FCAM", "RCAM", "ACAM", "SCS", "DIP", "TCC", "TM"]
        device_ids = ["vic", "rdc", "adc", "fcam", "rcam", "acam", "scs", "dip", "tcc", "tm"]
        
        self._current_devices = []
        for device_id, name in zip(device_ids, device_names):
            connected = payload.devices.get(name, False)
            self._current_devices.append(
                DeviceStatus(
                    device_id=device_id,
                    name=name,
                    connected=connected,
                    warning=False,
                    error_reason=None if connected else "연결 안 됨"
                )
            )
        
        # 비상정지 상태
        emergency = EmergencyStatus()
        emergency.communication_lost = payload.emergency_status.get("통신 두절", False)
        emergency.equipment_fail_driving = payload.emergency_status.get("장비고장(주행)", False)
        emergency.equipment_fail_power = payload.emergency_status.get("장비고장(동력계)", False)
        emergency.signal_lost_driving = payload.emergency_status.get("신호단절(주행)", False)
        emergency.signal_lost_autonomous = payload.emergency_status.get("신호단절(자율)", False)
        emergency.signal_lost_navigation = payload.emergency_status.get("신호단절(항법)", False)
        emergency.signal_lost_power = payload.emergency_status.get("신호단절(동력계)", False)
        emergency.signal_lost_comm = payload.emergency_status.get("신호단절(통신)", False)
        emergency.manual_stop_ocs = payload.emergency_status.get("수동정지(운용통제장치)", False)
        emergency.manual_stop_near = payload.emergency_status.get("수동정지(근거리조종기)", False)
        self._current_emergency = emergency
    
    def _add_log_entry(self, result: 'ParseResult', timestamp: datetime) -> None:
        """
        로그 엔트리 추가.
        
        Args:
            result: 파싱 결과
            timestamp: 수신 시간
        """
        log = LogEntry(
            timestamp=timestamp,
            sequence=result.header.sequence if result.header else 0,
            msg_code=f"0x{result.header.msg_code:02X}" if result.header else "???",
            parse_ok=result.success,
            checksum_ok=result.checksum_ok,
            mode=self._current_operation_mode,
            authority=self._current_authority,
            notes="" if result.success else (result.error or "파싱 실패")
        )
        
        # 최신 항목을 앞에 추가 (deque의 왼쪽)
        self._logs_history.appendleft(log)
    
    def _check_connection_timeout(self) -> None:
        """연결 타임아웃 체크."""
        if self._last_packet_time is None:
            return
        
        elapsed = (datetime.now() - self._last_packet_time).total_seconds()
        
        if elapsed >= config.ui.down_threshold_sec:
            self._is_connected = False
            
            if self._anomaly_detector:
                self._anomaly_detector.check_timeout(self._last_packet_time)
    
    def _update_availability_timeline(self) -> None:
        """가용성 타임라인 업데이트."""
        time_window = config.ui.timeline_duration_sec
        
        if not self._availability_segments:
            self._availability_segments = [
                AvailabilitySegment(0, time_window, self._is_connected)
            ]
            return
        
        last_seg = self._availability_segments[-1]
        
        # 상태 변화 확인
        if last_seg.is_up == self._is_connected:
            # 같은 상태 - 확장
            last_seg.end_sec = time_window
        else:
            # 상태 변경 - 새 세그먼트
            self._availability_segments.append(
                AvailabilitySegment(
                    start_sec=last_seg.end_sec,
                    end_sec=time_window,
                    is_up=self._is_connected
                )
            )
        
        # 오래된 세그먼트 정리
        if self._elapsed_time > time_window:
            self._prune_old_segments()
    
    def _prune_old_segments(self) -> None:
        """오래된 가용성 세그먼트 정리."""
        time_window = config.ui.timeline_duration_sec
        offset = self._elapsed_time - time_window
        
        pruned = []
        for seg in self._availability_segments:
            new_start = max(0, seg.start_sec - offset)
            new_end = max(0, seg.end_sec - offset)
            
            if new_end > 0:
                pruned.append(
                    AvailabilitySegment(new_start, new_end, seg.is_up)
                )
        
        if pruned:
            pruned[-1].end_sec = time_window
        
        self._availability_segments = pruned
    
    def _get_current_stats(self) -> Dict:
        """현재 통계 반환."""
        if self._stats_calc:
            return self._stats_calc.get_stats_dict()
        return {}
    
    def _calc_parse_success_rate(self) -> float:
        """파싱 성공률 계산."""
        if self._total_packets == 0:
            return 100.0
        return round((self._parse_success / self._total_packets) * 100, 1)
    
    def _calc_checksum_fail_rate(self) -> float:
        """체크섬 실패율 계산."""
        if self._total_packets == 0:
            return 0.0
        return round((self._checksum_fail / self._total_packets) * 100, 1)
    
    def _calc_availability(self, window_sec: int) -> float:
        """가용성 계산."""
        if self._stats_calc:
            return self._stats_calc.get_availability(window_sec)
        return 0.0
    
    def get_logs(self, limit: int = 50) -> List[Dict]:
        """
        로그 목록 반환.
        
        Args:
            limit: 최대 반환 개수
        
        Returns:
            로그 딕셔너리 리스트
        """
        with self._lock:
            return [log.to_dict() for log in list(self._logs_history)[:limit]]
    
    def clear_logs(self) -> None:
        """로그 초기화."""
        with self._lock:
            self._logs_history.clear()
    
    @property
    def log_count(self) -> int:
        """로그 개수."""
        return len(self._logs_history)


def get_data_provider(use_live: bool = None):
    """
    데이터 제공자 팩토리 함수.
    
    환경변수 또는 인자에 따라 Live 또는 Mock 제공자를 반환합니다.
    
    Args:
        use_live: True=Live, False=Mock, None=환경변수 확인
    
    Returns:
        LiveDataProvider 또는 MockDataGenerator 인스턴스
    
    환경변수:
        UGV_MON_USE_LIVE=true: Live 모드 활성화
    
    사용 예시:
        provider = get_data_provider()  # 환경변수에 따라 결정
        provider = get_data_provider(use_live=True)  # 강제 Live 모드
    """
    if use_live is None:
        use_live = os.getenv("UGV_MON_USE_LIVE", "").lower() == "true"
    
    if use_live:
        logger.info("Using LiveDataProvider (real-time capture)")
        return LiveDataProvider()
    else:
        logger.info("Using MockDataGenerator (simulated data)")
        from .mock_data import MockDataGenerator
        return MockDataGenerator()
