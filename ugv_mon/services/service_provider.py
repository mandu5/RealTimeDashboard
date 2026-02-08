"""
서비스 제공자 (브리지 패턴).

기존 콜백과의 호환성을 유지하면서 새로운 Service Layer를 사용합니다.
점진적 마이그레이션을 위한 브리지 역할을 합니다.

책임:
    1. 기존 DataProviderProtocol 인터페이스 구현
    2. 내부적으로 Service Layer 사용
    3. update_data() 호출 시 서비스들 조율

마이그레이션 완료 후:
    이 파일은 삭제하고 콜백에서 직접 서비스들을 호출할 수 있습니다.
"""

import logging
from datetime import datetime
from threading import Lock
from typing import Optional

from .dashboard_builder import DashboardBuilder
from ..pipeline.icd_parser import ICDParser
from ..pipeline.processor import PacketProcessor
from ..pipeline.queue import PacketQueue
from ..config import config
from ..store.packet_store import PacketStore

# 직접 import로 순환 참조 방지
from .capture_service import CaptureService
from .ml_service import MLService
from .stats_service import StatsService

logger = logging.getLogger(__name__)


class ServiceProvider:
    """서비스 통합 제공자.

    기존 LiveDataProvider와 동일한 인터페이스를 제공하면서
    내부적으로 분리된 서비스들을 사용합니다.

    Args:
        interface: 네트워크 인터페이스 이름
    """

    def __init__(self, interface: Optional[str] = None):
        self._interface = interface or config.network.interface
        self._lock = Lock()

        # =========================================================
        # 컴포넌트 초기화 (Composition Root에서 이동)
        # =========================================================

        # 캡처 컴포넌트
        self._queue = PacketQueue(max_size=1000)
        self._parser = ICDParser()
        self._store = PacketStore(window_sec=3600)
        self._processor = PacketProcessor(self._queue, self._parser, self._store)

        # 서비스 레이어
        self._capture = CaptureService(
            interface=self._interface,
            queue=self._queue,
            vic_port=config.network.vic_port,
            ocs_port=config.network.ocs_port,
        )
        self._stats = StatsService(timeout_sec=config.ui.down_threshold_sec)
        self._ml = MLService()

        # 빌더
        self._builder = DashboardBuilder(self._store, self._stats)

        # 가용성 세그먼트 (이동 예정)
        self._start_time = datetime.now()
        self._availability_segments: list[dict] = []
        self._last_avail_change_time: Optional[datetime] = None
        self._last_avail_state: Optional[bool] = None

    # =========================================================================
    # 캡처 제어 (CaptureService 위임)
    # =========================================================================

    def start_capture(self) -> bool:
        """캡처 시작."""
        return self._capture.start()

    def stop_capture(self) -> None:
        """캡처 중지."""
        self._capture.stop()

    def toggle_connection(self) -> bool:
        """연결 토글."""
        with self._lock:
            result = self._capture.toggle()
            if not result:
                self._store.reset_stream_state()
            else:
                self._store.reset_stream_state()
            return result

    def toggle_direction(self) -> str:
        """방향 전환."""
        with self._lock:
            self._stats.reset()
            self._store.reset()
            return self._capture.toggle_direction()

    @property
    def current_direction(self) -> str:
        """현재 방향."""
        return self._capture.direction

    @property
    def _is_connected(self) -> bool:
        """연결 상태 (호환성)."""
        return self._capture.is_running

    # =========================================================================
    # 데이터 생성 (콜백 호출)
    # =========================================================================

    def generate_initial_data(self) -> dict:
        """초기 데이터 생성."""
        return self._build_data()

    def update_data(self, prev_data: dict) -> dict:
        """데이터 업데이트 (폴링 시 호출).

        1. Processor 호출 → 파싱 수행
        2. Stats 업데이트
        3. 가용성 세그먼트 기록
        4. Dict 빌드
        """
        with self._lock:
            # 1. 패킷 처리
            result = self._processor.process_pending()

            # 2. 통계 업데이트
            self._stats.update(result)

            # 3. 가용성 세그먼트 기록
            is_connected = self._stats.is_connected()
            self._record_uptime_segment(is_connected)

            # 4. 연결 상태 기록
            self._store.record_connection_change(is_connected)

            return self._build_data()

    def _build_data(self) -> dict:
        """Dict 빌드."""
        is_connected = self._stats.is_connected()

        # ML 예측
        ml_data = self._ml.predict(self._store)

        # 가용성 세그먼트
        avail_segments = self._build_availability_segments()

        return self._builder.build(
            is_connected=is_connected,
            direction=self._capture.direction,
            filter_str=self._capture.filter_str,
            interface=self._capture.interface,
            ml_data=ml_data,
            availability_segments=avail_segments,
        )

    # =========================================================================
    # 가용성 세그먼트 (live_provider에서 이동)
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
        """보관 기간 초과 세그먼트 제거."""
        now = datetime.now()
        cutoff = (now - self._start_time).total_seconds() - max_sec
        self._availability_segments = [
            seg for seg in self._availability_segments if seg["end"] > cutoff
        ]

    def _build_availability_segments(self) -> list[dict]:
        """가용성 세그먼트 반환."""
        timeline_sec = config.ui.timeline_duration_sec
        now = datetime.now()
        current_offset = (now - self._start_time).total_seconds()
        is_connected = self._stats.is_connected()

        if not self._availability_segments:
            return [{"start": 0, "end": timeline_sec, "isUp": is_connected}]

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
                    "isUp": self._last_avail_state if self._last_avail_state is not None else is_connected,
                })

        return normalized if normalized else [{"start": 0, "end": timeline_sec, "isUp": is_connected}]

    # =========================================================================
    # 로그 관련 (호환성)
    # =========================================================================

    def get_logs(self, limit: int = 50) -> list[dict]:
        """로그 목록."""
        return self._store.get_logs(limit=limit)

    def clear_logs(self) -> None:
        """로그 초기화."""
        self._store.reset()
        self._stats.reset()
        self._ml.reset()

    @property
    def log_count(self) -> int:
        """로그 수."""
        return self._store.record_count
