"""
Alert System for UGV-MON Dashboard.

알림 조건 정의, 상태 관리, 토스트 알림 생성.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """알림 레벨."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """알림 데이터."""
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = f"{self.level.value}_{self.timestamp.strftime('%H%M%S%f')}"


class AlertManager:
    """알림 관리자 - 조건 체크 및 알림 생성."""
    
    # 알림 조건 임계값
    AVAILABILITY_THRESHOLD = 95.0  # 가용성 < 95%
    JITTER_P99_THRESHOLD = 100.0   # 지터 P99 > 100ms
    DISCONNECT_THRESHOLD = 5.0     # 연결 끊김 5초
    
    def __init__(self):
        self._last_connected_time: Optional[datetime] = None
        self._last_alert_time: Dict[str, datetime] = {}
        self._cooldown_seconds = 30  # 동일 알림 재발생 쿨다운
        self._pending_alerts: List[Alert] = []
    
    def check_conditions(self, data: Dict) -> List[Alert]:
        """
        대시보드 데이터를 기반으로 알림 조건 체크.
        
        Returns:
            생성된 알림 리스트
        """
        alerts = []
        now = datetime.now()
        
        # 1. 가용성 체크
        availability = data.get("availability5min", 100.0)
        if availability < self.AVAILABILITY_THRESHOLD:
            alert = self._create_alert_if_not_cooldown(
                "availability",
                AlertLevel.WARNING,
                "가용성 저하",
                f"5분 가용성이 {availability:.1f}%로 임계값({self.AVAILABILITY_THRESHOLD}%) 미만입니다.",
                now
            )
            if alert:
                alerts.append(alert)
        
        # 2. 지터 체크
        jitter_p99 = data.get("jitterP99", 0.0)
        if jitter_p99 > self.JITTER_P99_THRESHOLD:
            alert = self._create_alert_if_not_cooldown(
                "jitter",
                AlertLevel.WARNING,
                "지터 증가",
                f"P99 지터가 {jitter_p99:.1f}ms로 임계값({self.JITTER_P99_THRESHOLD}ms) 초과입니다.",
                now
            )
            if alert:
                alerts.append(alert)
        
        # 3. 연결 상태 체크
        is_connected = data.get("connected", True)
        if is_connected:
            self._last_connected_time = now
        elif self._last_connected_time:
            disconnect_duration = (now - self._last_connected_time).total_seconds()
            if disconnect_duration >= self.DISCONNECT_THRESHOLD:
                alert = self._create_alert_if_not_cooldown(
                    "disconnect",
                    AlertLevel.ERROR,
                    "연결 끊김",
                    f"연결이 {disconnect_duration:.0f}초 동안 끊어져 있습니다.",
                    now
                )
                if alert:
                    alerts.append(alert)
        
        self._pending_alerts.extend(alerts)
        return alerts
    
    def _create_alert_if_not_cooldown(
        self, 
        alert_type: str, 
        level: AlertLevel, 
        title: str, 
        message: str, 
        now: datetime
    ) -> Optional[Alert]:
        """쿨다운 체크 후 알림 생성."""
        last_time = self._last_alert_time.get(alert_type)
        if last_time and (now - last_time).total_seconds() < self._cooldown_seconds:
            return None
        
        self._last_alert_time[alert_type] = now
        return Alert(level=level, title=title, message=message, timestamp=now)
    
    def get_pending_alerts(self) -> List[Alert]:
        """대기 중인 알림 반환 및 클리어."""
        alerts = self._pending_alerts.copy()
        self._pending_alerts.clear()
        return alerts
    
    def reset(self):
        """상태 초기화."""
        self._last_connected_time = None
        self._last_alert_time.clear()
        self._pending_alerts.clear()


def create_toast_notification(alert: Alert) -> dict:
    """
    DMC Notification 컴포넌트용 props 딕셔너리 생성.
    
    Returns:
        dmc.Notification에 전달할 props
    """
    color_map = {
        AlertLevel.INFO: "blue",
        AlertLevel.WARNING: "yellow",
        AlertLevel.ERROR: "red",
        AlertLevel.CRITICAL: "red",
    }
    
    icon_map = {
        AlertLevel.INFO: "ℹ️",
        AlertLevel.WARNING: "⚠️",
        AlertLevel.ERROR: "❌",
        AlertLevel.CRITICAL: "🚨",
    }
    
    return {
        "id": alert.id,
        "title": f"{icon_map.get(alert.level, '')} {alert.title}",
        "message": alert.message,
        "color": color_map.get(alert.level, "gray"),
        "autoClose": 5000 if alert.level in [AlertLevel.INFO, AlertLevel.WARNING] else False,
    }
