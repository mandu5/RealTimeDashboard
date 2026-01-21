"""
공통 유틸리티 함수 - 색상, 스타일 헬퍼.
"""

from typing import Dict, Literal

StatusVariant = Literal["success", "warning", "destructive", "default", "info"]


def get_status_color(variant: StatusVariant) -> Dict[str, str]:
    """상태별 색상 스키마."""
    color_map = {
        "success": {"bg": "#d1fae5", "border": "#a7f3d0", "text": "#065f46"},
        "warning": {"bg": "#fef3c7", "border": "#fde68a", "text": "#92400e"},
        "destructive": {"bg": "#fee2e2", "border": "#fecaca", "text": "#991b1b"},
        "info": {"bg": "#dbeafe", "border": "#bfdbfe", "text": "#1e40af"},
        "default": {"bg": "#f1f5f9", "border": "#e2e8f0", "text": "#334155"},
    }
    return color_map.get(variant, color_map["default"])


def get_device_status_style(connected: bool, warning: bool = False) -> Dict[str, str]:
    """장치 상태별 스타일."""
    if not connected:
        return {"backgroundColor": "#fee2e2", "border": "1px solid #fecaca", "color": "#991b1b"}
    elif warning:
        return {"backgroundColor": "#fef3c7", "border": "1px solid #fde68a", "color": "#92400e"}
    else:
        return {"backgroundColor": "#d1fae5", "border": "1px solid #a7f3d0", "color": "#065f46"}


def get_chart_colors() -> Dict[str, str]:
    """차트 색상 팔레트."""
    return {
        "primary": "#3b82f6",
        "secondary": "#10b981",
        "p95_line": "#f59e0b",
        "p99_line": "#ef4444",
        "fill_primary": "rgba(59, 130, 246, 0.1)",
        "fill_secondary": "rgba(16, 185, 129, 0.1)",
        "up_segment": "#10b981",
        "down_segment": "#ef4444",
        "grid": "#f1f5f9",
    }
