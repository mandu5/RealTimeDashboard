"""
UGV-MON 공통 UI 스타일 정의.

모든 인라인 스타일을 중앙화하여 재사용성과 일관성을 높입니다.
"""

# =============================================================================
# 색상 팔레트
# =============================================================================
from typing import Optional

COLORS = {
    # 주요 색상
    "primary": "#3b82f6",
    "primary_dark": "#1e40af",
    "success": "#22c55e",
    "success_dark": "#059669",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "purple": "#9333ea",

    # 텍스트
    "text_dark": "#0f172a",
    "text_primary": "#1e293b",
    "text_secondary": "#334155",
    "text_muted": "#64748b",

    # 배경
    "bg_page": "linear-gradient(to bottom right, #f8fafc, #f1f5f9)",
    "bg_card": "white",
    "border": "#e2e8f0",
    "border_light": "#e5e7eb",

    # 상태별 배경 그라데이션
    "bg_success": "linear-gradient(to bottom right, #d1fae5, #a7f3d0)",
    "bg_info": "linear-gradient(to bottom right, #dbeafe, #bfdbfe)",
    "bg_neutral": "linear-gradient(to bottom right, #f1f5f9, #e2e8f0)",
    "bg_error": "#fee2e2",
}

# =============================================================================
# 공통 스타일
# =============================================================================

# 패널 헤더 (타이틀 + 인디케이터)
PANEL_HEADER = {
    "display": "flex",
    "alignItems": "center",
    "gap": "8px",
    "marginBottom": "16px",
}

# 수직 인디케이터 바
def indicator_bar(color: Optional[str] = None) -> dict:
    return {
        "width": "4px",
        "height": "16px",
        "backgroundColor": color or COLORS["primary"],
        "borderRadius": "9999px",
    }

# 패널 타이틀 텍스트
PANEL_TITLE = {
    "fontSize": "14px",
    "fontWeight": "600",
    "color": COLORS["text_secondary"],
}

# 카드 기본 스타일
CARD_MARGIN = {"marginBottom": "24px"}

# 페이지 컨테이너
PAGE_CONTAINER = {
    "minHeight": "100vh",
    "background": COLORS["bg_page"],
    "padding": "24px",
    "fontFamily": "Inter, sans-serif",
}

# 헤더 바
HEADER_BAR = {
    "backgroundColor": COLORS["bg_card"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "12px",
    "padding": "16px 24px",
    "marginBottom": "24px",
    "boxShadow": "0 1px 3px 0 rgba(0, 0, 0, 0.1)",
}

# 2개 컬럼 그리드
TWO_COLUMN_GRID = {
    "display": "grid",
    "gridTemplateColumns": "repeat(2, 1fr)",
    "gap": "24px",
    "marginBottom": "24px",
}

# 7개 컬럼 그리드 (KPI 카드)
KPI_GRID = {
    "display": "grid",
    "gridTemplateColumns": "repeat(7, 1fr)",
    "gap": "16px",
    "marginBottom": "24px",
}

# Flex 컬럼
FLEX_COLUMN = {
    "display": "flex",
    "flexDirection": "column",
}

# Flex Row (gap 포함)
def flex_row(gap: str = "8px") -> dict:
    return {
        "display": "flex",
        "alignItems": "center",
        "gap": gap,
    }

# =============================================================================
# 값 표시 스타일
# =============================================================================

VALUE_LARGE = {
    "fontSize": "24px",
    "fontWeight": "700",
    "color": COLORS["text_dark"],
}

VALUE_MEDIUM = {
    "fontSize": "16px",
    "fontWeight": "700",
}

UNIT_SMALL = {
    "fontSize": "12px",
    "color": COLORS["text_muted"],
    "fontWeight": "500",
    "marginLeft": "4px",
}

LABEL_SMALL = {
    "fontSize": "11px",
    "color": COLORS["text_muted"],
    "fontWeight": "500",
    "marginBottom": "8px",
}

# =============================================================================
# 헬퍼 함수
# =============================================================================

def status_box_style(bg_gradient: str, border_color: str) -> dict:
    """상태 박스 (운용모드 등) 스타일 생성."""
    return {
        "background": bg_gradient,
        "padding": "16px",
        "borderRadius": "8px",
        "border": f"1px solid {border_color}",
    }

def led_style(is_active: bool, custom_color: Optional[str] = None) -> dict:
    """LED 인디케이터 스타일.

    Args:
        is_active: 활성 상태
        custom_color: 커스텀 색상 (None이면 기본 빨간색/회색)
    """
    if custom_color and is_active:
        color = custom_color
        shadow = f"0 0 12px {custom_color}80"  # 80 = 50% opacity
    elif is_active:
        color = COLORS["error"]
        shadow = "0 0 12px rgba(239, 68, 68, 0.5)"
    else:
        color = "#cbd5e1"
        shadow = "none"

    return {
        "width": "8px",
        "height": "8px",
        "borderRadius": "9999px",
        "backgroundColor": color,
        "boxShadow": shadow,
    }


# =============================================================================
# 상태 색상 헬퍼 (기존 helpers.py에서 통합)
# =============================================================================

def get_status_color(variant: str) -> dict:
    """상태별 색상 스키마."""
    color_map = {
        "success": {"bg": "#d1fae5", "border": "#a7f3d0", "text": "#065f46"},
        "warning": {"bg": "#fef3c7", "border": "#fde68a", "text": "#92400e"},
        "destructive": {"bg": "#fee2e2", "border": "#fecaca", "text": "#991b1b"},
        "info": {"bg": "#dbeafe", "border": "#bfdbfe", "text": "#1e40af"},
        "default": {"bg": "#f1f5f9", "border": "#e2e8f0", "text": "#334155"},
    }
    return color_map.get(variant, color_map["default"])


def get_device_status_style(connected: bool, warning: bool = False) -> dict:
    """장치 상태별 스타일."""
    if not connected:
        return {"backgroundColor": "#fee2e2", "border": "1px solid #fecaca", "color": "#991b1b"}
    elif warning:
        return {"backgroundColor": "#fef3c7", "border": "1px solid #fde68a", "color": "#92400e"}
    return {"backgroundColor": "#d1fae5", "border": "1px solid #a7f3d0", "color": "#065f46"}


def get_chart_colors() -> dict:
    """차트 색상 팔레트."""
    return {
        "primary": "#3b82f6",
        "secondary": "#10b981",
        "p95_line": "#f59e0b",
        "fill_primary": "rgba(59, 130, 246, 0.1)",
        "fill_secondary": "rgba(16, 185, 129, 0.1)",
        "up_segment": "#10b981",
        "down_segment": "#ef4444",
        "grid": "#f1f5f9",
    }
