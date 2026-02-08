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
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional

from ..core import config, DEVICE_NAMES
from ..core.models import EMERGENCY_SOURCE_NAMES

logger = logging.getLogger(__name__)

try:
    from ..capture import PacketSniffer, PacketQueue, PacketProcessor
    from ..parser import ICDParser
    from .packet_store import PacketStore
    from ..analysis import MLPipeline, FeatureExtractor, RuleDetector
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
        PacketQueue → PacketProcessor → PacketStore → _build_dashboard_data() → Dict
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
        
        # ML 이상 탐지
        self._ml_pipeline: Optional[MLPipeline] = None
        self._rule_detector: Optional[RuleDetector] = None  # 앙상블용
        self._ml_score_history: List[Dict] = []  # 최근 60개 점수 기록
        self._ml_records: List[Dict] = []  # 최근 100개 레코드
        
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
        # ML 파이프라인 초기화
        self._ml_pipeline = MLPipeline()
        self._rule_detector = RuleDetector()  # 앙상블용 Rule 탐지기
        # 기존 모델 로드 시도
        if self._ml_pipeline.load():
            logger.info("[ML] 저장된 모델 로드 완료")
        else:
            logger.info("[ML] 저장된 모델 없음, Rule 탐지만 활성화")

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

    # =========================================================================
    # 데이터 생성/업데이트
    # =========================================================================
    
    def generate_initial_data(self) -> Dict:
        """초기 대시보드 데이터 생성."""
        return self._build_dashboard_data()

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
            self._check_connection_timeout()
            
            # 가용성 상태 기록
            self._record_uptime_segment(self._is_connected)
            
            # 연결 상태 기록
            if self._store:
                self._store.record_connection_change(self._is_connected)
            
            return self._build_dashboard_data()

    def _check_connection_timeout(self):
        """연결 타임아웃 체크 (down_threshold_sec 초과 시 연결 해제)."""
        if self._last_packet_time:
            elapsed = (datetime.now() - self._last_packet_time).total_seconds()
            if elapsed >= config.ui.down_threshold_sec:
                self._is_connected = False

    # =========================================================================
    # 가용성 세그먼트 (회사 방식)
    # =========================================================================
    
    def _record_uptime_segment(self, new_is_up: bool) -> None:
        """연결 상태 변화 시 가용성(uptime) 세그먼트 기록."""
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
        self._prune_old_uptime_segments(max_sec=3600)

    def _prune_old_uptime_segments(self, max_sec: int = 3600) -> None:
        """보관 기간(max_sec) 초과 세그먼트 제거."""
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

    def _build_dashboard_data(self) -> Dict:
        """전체 대시보드 데이터 빌드 (25키).

        4개 하위 빌더의 결과를 병합하여 DashboardData 딕셔너리를 구성합니다.
        """
        return {
            **self._build_connection_info(),
            **self._build_kpi_metrics(),
            **self._build_operational_info(),
            **self._build_ui_display_data(),
            "ml": self._build_ml_data(),
        }

    def _build_connection_info(self) -> Dict:
        """연결 정보 (5키): 연결여부, 인터페이스, 방향, 필터, 마지막 패킷 시각."""
        return {
            "connected": self._is_connected,
            "interface": self._interface,
            "direction": self._current_direction,
            "filter": f"{self._src_port}→{self._dst_port}",
            "lastPacketTime": self._last_packet_time.strftime("%H:%M:%S") if self._last_packet_time else "",
        }

    def _build_kpi_metrics(self) -> Dict:
        """KPI 지표 (8키): PPS, 파싱률, 체크섬, 손실, 가용성, 지터."""
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
        }

    def _build_operational_info(self) -> Dict:
        """운용 정보 (4키): 운용모드, 권한, 주행상태, 비상정지."""
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
            "emergencyStatus": {name: False for name in EMERGENCY_SOURCE_NAMES} | {"처리완료": False},
        }

    def _build_ui_display_data(self) -> Dict:
        """UI 렌더링용 데이터 (7키): 차트, 장치, 가용성, 이력."""
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

    # =========================================================================
    # ML 이상 탐지
    # =========================================================================

    def _build_ml_data(self) -> Dict:
        """앙상블 이상 탐지 데이터 빌드.
        
        Rule-Based + ML 앙상블:
        1. Rule 탐지는 항상 실행 (Cold Start 대응)
        2. ML은 학습 완료 후 실행
        3. 둘 중 하나라도 이상이면 최종 이상 판정
        """
        now = datetime.now()
        
        # 현재 통계 가져오기
        if not self._store:
            return {"model_status": "not_ready"}
        
        current_stats = self._get_current_stats_for_ml()
        
        # 레코드 히스토리 업데이트
        self._update_ml_records(current_stats, now)
        
        # === Rule-Based 탐지 (항상 실행) ===
        rule_result = None
        if self._rule_detector:
            rule_result = self._rule_detector.detect(current_stats)
        
        # === ML 탐지 (학습 후 실행) ===
        ml_result = None
        ml_ready = False
        
        if self._ml_pipeline:
            if not self._ml_pipeline.is_ready:
                # 학습 시도
                stats_history = self._store.get_stats_history(limit=500)
                if len(stats_history) >= 500:
                    self._ml_pipeline.train(stats_history)
                    logger.info("[ML] 자동 학습 완료, 앙상블 모드 활성화")
                    ml_ready = True
            else:
                ml_ready = True
            
            if ml_ready:
                ml_result = self._ml_pipeline.predict(current_stats)
                self._update_ml_score_history(ml_result.anomaly_score, now)
        
        # === 앙상블 판정 ===
        rule_anomaly = rule_result.is_anomaly if rule_result else False
        ml_anomaly = ml_result.is_anomaly if ml_result else False
        final_anomaly = rule_anomaly or ml_anomaly
        
        # 탐지 소스 결정
        if rule_anomaly and ml_anomaly:
            detection_source = "Both"
        elif rule_anomaly:
            detection_source = "Rule"
        elif ml_anomaly:
            detection_source = "ML"
        else:
            detection_source = None
        
        # 신뢰도 계산
        if ml_result:
            confidence = ml_result.confidence
        elif final_anomaly:
            confidence = 0.7  # Rule만 있을 때 기본 신뢰도
        else:
            confidence = 0.0
        
        # 기여 특성
        contributing_features = []
        if ml_result and ml_result.contributing_features:
            contributing_features = [
                {"name": f["name"], "z_score": f["z_score"]}
                for f in ml_result.contributing_features
            ]
        elif rule_result and rule_result.violated_rules:
            # Rule 위반을 기여 특성으로 변환
            for rule in rule_result.violated_rules:
                contributing_features.append({
                    "name": rule,
                    "z_score": 2.5,  # Rule 위반은 고정 z-score
                })
        
        return {
            "model_status": "ready" if ml_ready else "rule_only",
            "is_anomaly": final_anomaly,
            "anomaly_score": ml_result.anomaly_score if ml_result else (-0.5 if final_anomaly else 0.0),
            "confidence": confidence,
            "detection_source": detection_source,  # 새 필드: Rule/ML/Both
            "rule_violated": rule_result.violated_rules if rule_result else [],
            "contributing_features": contributing_features,
            "records": self._ml_records[-100:],
            "score_history": self._ml_score_history[-60:],
        }

    def _get_current_stats_for_ml(self) -> Dict:
        """PacketStore에서 ML용 통계 추출."""
        if not self._store:
            return {}
        
        return {
            "jitter_current": self._store.last_jitter or 0,
            "jitter_p95": self._store.get_jitter_p95() or 0,
            "pps": self._store.pps,
            "loss_rate": self._store.packet_loss_rate,
            # 추가 통계 (FeatureExtractor에서 계산)
            "parse_success_rate": self._store.get_parse_success_rate(),
            "checksum_fail_rate": self._store.get_checksum_fail_rate(),
        }

    def _update_ml_records(self, stats: Dict, now: datetime):
        """3D 차트용 레코드 히스토리 업데이트."""
        record = {
            "timestamp": now.strftime("%H:%M:%S"),
            "jitter_current": stats.get("jitter_current", 0),
            "pps": stats.get("pps", 0),
            "loss_rate": stats.get("loss_rate", 0),
            "anomaly_score": 0,  # 추론 후 업데이트
        }
        self._ml_records.append(record)
        # 최대 200개 유지
        if len(self._ml_records) > 200:
            self._ml_records = self._ml_records[-200:]

    def _update_ml_score_history(self, score: float, now: datetime):
        """타임라인용 점수 히스토리 업데이트."""
        self._ml_score_history.append({
            "timestamp": now.strftime("%H:%M:%S"),
            "score": score,
        })
        # 최대 120개 유지
        if len(self._ml_score_history) > 120:
            self._ml_score_history = self._ml_score_history[-120:]
        
        # 레코드에 점수 반영
        if self._ml_records:
            self._ml_records[-1]["anomaly_score"] = score

