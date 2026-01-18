"""
Utility helper functions for UGV-MON Dashboard.

Provides common utilities for:
- Color mapping based on status/variant
- Data formatting (percentages, timestamps)
- Style generation for consistent theming
"""

from datetime import datetime
from typing import Dict, Literal, Tuple


# Type definitions for status variants
StatusVariant = Literal["success", "warning", "destructive", "default", "info"]


def get_status_color(variant: StatusVariant) -> Dict[str, str]:
    """
    Get color scheme for a status variant.
    
    Used for consistent color theming across status chips, badges, and indicators.
    Colors follow enterprise dashboard conventions with clear semantic meaning.
    
    Args:
        variant: Status type - 'success', 'warning', 'destructive', 'default', 'info'
    
    Returns:
        Dictionary with 'bg', 'border', 'text' color hex values
        
    Example:
        >>> colors = get_status_color('success')
        >>> print(colors['bg'])  # '#d1fae5'
    """
    color_map = {
        "success": {
            "bg": "#d1fae5",
            "border": "#a7f3d0", 
            "text": "#065f46"
        },
        "warning": {
            "bg": "#fef3c7",
            "border": "#fde68a",
            "text": "#92400e"
        },
        "destructive": {
            "bg": "#fee2e2",
            "border": "#fecaca",
            "text": "#991b1b"
        },
        "info": {
            "bg": "#dbeafe",
            "border": "#bfdbfe",
            "text": "#1e40af"
        },
        "default": {
            "bg": "#f1f5f9",
            "border": "#e2e8f0",
            "text": "#334155"
        },
    }
    
    return color_map.get(variant, color_map["default"])


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format a percentage value for display.
    
    Args:
        value: Percentage value (0-100)
        decimals: Number of decimal places
        
    Returns:
        Formatted string like "99.9%"
    """
    return f"{value:.{decimals}f}%"


def format_timestamp(dt: datetime, include_date: bool = False) -> str:
    """
    Format a datetime for display in logs and UI.
    
    Args:
        dt: Datetime object
        include_date: Whether to include date portion
        
    Returns:
        Formatted string like "14:32:05" or "2024-01-15 14:32:05"
    """
    if include_date:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return dt.strftime("%H:%M:%S")


def get_device_status_style(connected: bool, warning: bool = False) -> Dict[str, str]:
    """
    Get style for device connection indicator.
    
    Args:
        connected: Whether device is connected
        warning: Whether device has a warning condition
        
    Returns:
        Style dictionary with backgroundColor, border, color
    """
    if not connected:
        return {
            "backgroundColor": "#fee2e2",
            "border": "1px solid #fecaca",
            "color": "#991b1b"
        }
    elif warning:
        return {
            "backgroundColor": "#fef3c7",
            "border": "1px solid #fde68a",
            "color": "#92400e"
        }
    else:
        return {
            "backgroundColor": "#d1fae5",
            "border": "1px solid #a7f3d0",
            "color": "#065f46"
        }


def get_chart_colors() -> Dict[str, str]:
    """
    Get standard chart color palette.
    
    Returns:
        Dictionary with named colors for chart elements
    """
    return {
        "primary": "#3b82f6",      # Blue - PPS line
        "secondary": "#10b981",    # Green - Jitter line
        "p95_line": "#f59e0b",     # Amber - P95 reference
        "p99_line": "#ef4444",     # Red - P99 reference
        "fill_primary": "rgba(59, 130, 246, 0.1)",
        "fill_secondary": "rgba(16, 185, 129, 0.1)",
        "up_segment": "#10b981",   # Green - availability up
        "down_segment": "#ef4444", # Red - availability down
        "grid": "#f1f5f9",
    }


def calculate_availability(
    up_duration_sec: float,
    total_duration_sec: float
) -> float:
    """
    Calculate availability percentage.
    
    Args:
        up_duration_sec: Total uptime in seconds
        total_duration_sec: Total monitoring duration in seconds
        
    Returns:
        Availability percentage (0-100)
    """
    if total_duration_sec <= 0:
        return 100.0
    return (up_duration_sec / total_duration_sec) * 100.0


def get_operation_mode_label(mode_bits: int) -> str:
    """
    Convert operation mode bits to Korean label.
    
    Based on ICD v1.0: bits 7..5 of VIC state byte
    
    Args:
        mode_bits: 3-bit operation mode value (0-4)
        
    Returns:
        Korean label for operation mode
    """
    mode_labels = {
        0b000: "준비 (PREP)",
        0b001: "전환 중 (TRANSITION)",
        0b010: "무인 주행 (UNMANNED DRIVING)",
        0b011: "무인 사격 (UNMANNED FIRING)",
        0b100: "비상 정지 (EMERGENCY STOP)",
    }
    return mode_labels.get(mode_bits, f"알 수 없음 ({mode_bits})")


def get_authority_label(authority_bits: int) -> str:
    """
    Convert authority bits to Korean label.
    
    Based on ICD v1.0: bits 3..2 of VIC state byte
    
    Args:
        authority_bits: 2-bit authority value (0-2)
        
    Returns:
        Korean label for authority
    """
    authority_labels = {
        0b00: "해제됨 (RELEASED)",
        0b01: "OCS 획득 (OCS ACQUIRED)",
        0b10: "근거리조종기 (NEAR CONTROLLER)",
    }
    return authority_labels.get(authority_bits, f"알 수 없음 ({authority_bits})")


def get_driving_state_label(driving_bits: int) -> str:
    """
    Convert driving state bits to Korean label.
    
    Based on ICD v1.0: bits 1..0 of VIC state byte
    
    Args:
        driving_bits: 2-bit driving state value (1-3)
        
    Returns:
        Korean label for driving state
    """
    driving_labels = {
        0b01: "원격 (REMOTE)",
        0b10: "군집 (PLATOON)",
        0b11: "자율 파견 (AUTONOMOUS DISPATCH)",
    }
    return driving_labels.get(driving_bits, f"알 수 없음 ({driving_bits})")


def seq_gap_with_rollover(prev_seq: int, curr_seq: int, max_seq: int = 256) -> int:
    """
    Calculate sequence gap accounting for rollover.
    
    Args:
        prev_seq: Previous sequence number
        curr_seq: Current sequence number
        max_seq: Maximum sequence value (256 for 8-bit)
        
    Returns:
        Gap value (expected gap is 1 for consecutive packets)
    """
    if curr_seq >= prev_seq:
        return curr_seq - prev_seq
    else:
        # Rollover occurred
        return (max_seq - prev_seq) + curr_seq
