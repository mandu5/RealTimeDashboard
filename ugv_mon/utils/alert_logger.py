"""
Alert Logger for UGV-MON Dashboard.

알림 이벤트를 로그 파일에 기록.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .alerts import Alert

# 로그 디렉토리 설정
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
ALERT_LOG_FILE = LOG_DIR / "alerts.log"


def get_alert_logger() -> logging.Logger:
    """알림 전용 로거 생성."""
    logger = logging.getLogger("ugv_mon.alerts")
    
    if not logger.handlers:
        # 디렉토리 생성
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # 파일 핸들러
        file_handler = logging.FileHandler(ALERT_LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        
        # 포맷 설정
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    
    return logger


def log_alert(alert: "Alert") -> None:
    """알림을 로그 파일에 기록."""
    logger = get_alert_logger()
    
    level_map = {
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    
    level = level_map.get(alert.level.value, logging.INFO)
    message = f"[{alert.title}] {alert.message}"
    
    logger.log(level, message)


def get_alert_log_path() -> str:
    """알림 로그 파일 경로 반환."""
    return str(ALERT_LOG_FILE)
