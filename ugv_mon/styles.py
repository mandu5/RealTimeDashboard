"""
UGV-MON 공통 UI 스타일 정의.

UI 컴포넌트에서 사용되는 스타일 상수를 중앙 집중화합니다.
"""

from typing import Dict

# =============================================================================
# 색상 팔레트
# =============================================================================

# 주요 색상
COLORS = {
    "primary": "#3b82f6",          # Blue
    "primary_dark": "#1e40af",
    "secondary": "#64748b",        # Slate
    "success": "#22c55e",          # Green
    "success_bg": "#dcfce7",
    "warning": "#f59e0b",          # Amber
    "warning_bg": "#fef3c7",
    "error": "#ef4444",            # Red
    "error_bg": "#fee2e2",
    "purple": "#9333ea",
    "purple_dark": "#7c3aed",
    
    # 텍스트 색상
    "text_primary": "#0f172a",     # Slate 900
    "text_secondary": "#334155",   # Slate 700
    "text_muted": "#64748b",       # Slate 500
    
    # 배경 색상
    "bg_gradient_start": "#f8fafc",
    "bg_gradient_end": "#f1f5f9",
    "border": "#e2e8f0",
    "border_light": "#e5e7eb",
}

# =============================================================================
# 폰트 스타일
# =============================================================================

FONTS = {
    "family": "Inter, sans-serif",
    "family_mono": "monospace",
}

FONT_SIZES = {
    "xs": "11px",
    "sm": "12px",
    "md": "13px",
    "base": "14px",
    "lg": "16px",
    "xl": "20px",
    "2xl": "24px",
}

FONT_WEIGHTS = {
    "normal": "400",
    "medium": "500",
    "semibold": "600",
    "bold": "700",
}

# =============================================================================
# 공통 스타일 함수
# =============================================================================

def panel_header_style() -> Dict:
    """패널 헤더 공통 스타일."""
    return {
        "display": "flex",
        "alignItems": "center",
        "gap": "8px",
        "marginBottom": "16px",
    }


def panel_title_style() -> Dict:
    """패널 타이틀 공통 스타일."""
    return {
        "fontSize": FONT_SIZES["base"],
        "fontWeight": FONT_WEIGHTS["semibold"],
        "color": COLORS["text_secondary"],
    }


def panel_indicator_style(color: str = None) -> Dict:
    """패널 인디케이터 (수직 바) 스타일."""
    return {
        "width": "4px",
        "height": "16px",
        "backgroundColor": color or COLORS["primary"],
        "borderRadius": "9999px",
    }


def kpi_value_style() -> Dict:
    """KPI 값 표시 스타일."""
    return {
        "fontSize": FONT_SIZES["2xl"],
        "fontWeight": FONT_WEIGHTS["bold"],
        "color": COLORS["text_primary"],
    }


def kpi_unit_style() -> Dict:
    """KPI 단위 표시 스타일."""
    return {
        "fontSize": FONT_SIZES["sm"],
        "color": COLORS["text_muted"],
        "fontWeight": FONT_WEIGHTS["medium"],
        "marginLeft": "4px",
    }


def kpi_label_style() -> Dict:
    """KPI 라벨 스타일."""
    return {
        "fontSize": FONT_SIZES["xs"],
        "color": COLORS["text_muted"],
        "fontWeight": FONT_WEIGHTS["medium"],
        "marginBottom": "8px",
    }


def status_ok_style() -> Dict:
    """정상 상태 스타일."""
    return {
        "color": COLORS["success"],
        "backgroundColor": COLORS["success_bg"],
    }


def status_warning_style() -> Dict:
    """경고 상태 스타일."""
    return {
        "color": COLORS["warning"],
        "backgroundColor": COLORS["warning_bg"],
    }


def status_error_style() -> Dict:
    """오류 상태 스타일."""
    return {
        "color": COLORS["error"],
        "backgroundColor": COLORS["error_bg"],
    }
