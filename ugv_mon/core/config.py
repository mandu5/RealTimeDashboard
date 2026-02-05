"""
UGV-MON Dashboard Configuration.

환경변수로 설정 가능:
- UGV_MON_PORT: 서버 포트 (기본: 8050)
- UGV_MON_INTERFACE: 캡처 인터페이스 (기본: lo)
- UGV_MON_POLL_INTERVAL: 폴링 간격 ms (기본: 2000)
"""

import os
from dataclasses import dataclass, field


@dataclass
class AppConfig:
    """앱 서버 설정."""
    name: str = "UGV-MON Dashboard"
    version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8050


@dataclass
class NetworkConfig:
    """네트워크 캡처 설정."""
    interface: str = "lo"
    # 양방향 캡처용 포트 (4주차 금요일)
    vic_port: int = 50000   # VIC → OCS (상태 메시지)
    ocs_port: int = 61000   # OCS → VIC (제어 메시지)


@dataclass
class UIConfig:
    """대시보드 UI 설정."""
    poll_interval_ms: int = 2000
    max_log_entries: int = 200
    max_chart_points: int = 60
    timeline_duration_sec: int = 3600
    down_threshold_sec: float = 5.0


@dataclass
class ThresholdConfig:
    """알림 임계값 설정."""
    jitter_warning_ms: float = 10.0
    jitter_critical_ms: float = 50.0
    availability_warning: float = 99.0
    availability_critical: float = 95.0


@dataclass
class Config:
    """전체 설정 컨테이너."""
    app: AppConfig = field(default_factory=AppConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    threshold: ThresholdConfig = field(default_factory=ThresholdConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """환경변수에서 설정 로드."""
        cfg = cls()
        
        if os.getenv("UGV_MON_DEBUG"):
            cfg.app.debug = os.getenv("UGV_MON_DEBUG").lower() == "true"
        if os.getenv("UGV_MON_PORT"):
            cfg.app.port = int(os.getenv("UGV_MON_PORT"))
        if os.getenv("UGV_MON_INTERFACE"):
            cfg.network.interface = os.getenv("UGV_MON_INTERFACE")
        if os.getenv("UGV_MON_POLL_INTERVAL"):
            cfg.ui.poll_interval_ms = int(os.getenv("UGV_MON_POLL_INTERVAL"))

        return cfg


# 전역 설정 인스턴스
config = Config.from_env()
