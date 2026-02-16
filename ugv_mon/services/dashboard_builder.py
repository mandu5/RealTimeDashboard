"""
대시보드 데이터 빌더.

Store와 Service에서 데이터를 가져와 Dict(25키)를 빌드합니다.
Single Responsibility: 데이터 조합 및 Dict 빌드만 수행.

책임:
    1. Store에서 통계/이력 조회
    2. StatsService에서 비율 계산치 조회
    3. Dict(25키) 조립

데이터 흐름:
    Store + Stats + CaptureInfo → DashboardBuilder → Dict(25키)

사용 예시:
    >>> builder = DashboardBuilder(store, stats)
    >>> data = builder.build(is_connected=True, direction="status", ...)
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..constants import DEVICE_NAMES
from ..models import EMERGENCY_SOURCE_NAMES

if TYPE_CHECKING:
    from ..store.packet_store import PacketStore
    from .stats_service import StatsService


class DashboardBuilder:
    """대시보드 데이터 빌더.

    Store와 Service에서 데이터를 가져와 Dict(25키)를 조립합니다.
    이 클래스는 상태를 가지지 않으며, 순수 함수처럼 동작합니다.

    Args:
        store: 패킷 저장소 (통계/이력 제공)
        stats: 통계 서비스 (비율 계산 제공)
    """

    def __init__(self, store: "PacketStore", stats: "StatsService"):
        self._store = store
        self._stats = stats
        self._start_time = datetime.now()

    def build(
        self,
        is_connected: bool,
        direction: str,
        filter_str: str,
        interface: str,
        ml_data: dict[str, Any],
    ) -> dict[str, Any]:
        """대시보드 데이터 빌드 (25키).

        Args:
            is_connected: 연결 상태
            direction: 캡처 방향 ("status" / "control")
            filter_str: BPF 필터 문자열
            interface: 네트워크 인터페이스
            ml_data: ML 서비스 결과

        Returns:
            DashboardData 딕셔너리 (25키)
        """
        return {
            **self._build_connection_info(is_connected, direction, filter_str, interface),
            **self._build_kpi_metrics(),
            **self._build_operational_info(),
            **self._build_ui_display_data(),
            "ml": ml_data,
        }

    # =========================================================================
    # 연결 정보 (5키)
    # =========================================================================

    def _build_connection_info(
        self,
        is_connected: bool,
        direction: str,
        filter_str: str,
        interface: str,
    ) -> dict:
        """연결 정보 빌드."""
        return {
            "connected": is_connected,
            "interface": interface,
            "direction": direction,
            "filter": filter_str,
            "lastPacketTime": self._stats.last_packet_time_str,
        }

    # =========================================================================
    # KPI 지표 (7키)
    # =========================================================================

    def _build_kpi_metrics(self) -> dict:
        """KPI 지표 빌드 (7개).

        Store에서: PPS, 패킷 손실, 가용성, 지터
        Stats에서: 파싱률, 체크섬률
        """
        store_stats = self._store.get_stats_dict() if self._store else {}

        return {
            # Store에서 가져오기
            "capturePps": store_stats.get("pps", 0),
            "packetLoss": store_stats.get("packet_loss", 0),
            "availability": store_stats.get("availability", 0.0),
            "jitterCurrent": store_stats.get("jitter_current", 0.0),
            "jitterP95": store_stats.get("jitter_p95", 0.0),
            # Stats에서 가져오기
            "parseSuccess": self._stats.get_parse_rate(),
            "checksumFail": self._stats.get_checksum_fail_rate(),
        }

    # =========================================================================
    # 운용 정보 (4키)
    # =========================================================================

    def _build_operational_info(self) -> dict:
        """운용 정보 빌드."""
        payload = self._stats.last_payload

        if payload:
            return {
                "operationalMode": payload.operation_mode,
                "operationalAuthority": payload.authority,
                "drivingState": payload.driving_state,
                "emergencyStatus": payload.get_emergency_dict(),
            }

        # 기본값
        return {
            "operationalMode": "--- (대기 중)",
            "operationalAuthority": "--- (대기 중)",
            "drivingState": "--- (대기 중)",
            "emergencyStatus": dict.fromkeys(EMERGENCY_SOURCE_NAMES, False) | {"처리완료": False},
        }

    # =========================================================================
    # UI 표시 데이터 (7키)
    # =========================================================================

    def _build_ui_display_data(self) -> dict:
        """UI 렌더링용 데이터 빌드."""
        # 장치 상태
        payload = self._stats.last_payload
        if payload:
            devices = [
                {"name": name, "connected": payload.devices.get(name, False)}
                for name in DEVICE_NAMES
            ]
        else:
            devices = [{"name": n, "connected": False} for n in DEVICE_NAMES]

        # Store에서 데이터 가져오기
        if self._store:
            chart_data = self._store.get_chart_data(limit=180)
            connection_history = self._store.get_connection_history(limit=10)
            mode_transitions = self._store.get_mode_transitions(limit=10)
            emergency_counts = self._store.get_emergency_counts()
        else:
            chart_data = []
            connection_history = []
            mode_transitions = []
            emergency_counts = {}

        logs = self._store.get_logs(limit=50) if self._store else []

        return {
            "combinedData": chart_data,
            "devices": devices,
            "connectionHistory": connection_history,
            "modeTransitions": mode_transitions,
            "emergencyCounts": emergency_counts,
            "logs": logs,
        }
