"""
Utility helper functions for UGV-MON Dashboard.

=============================================================================
대시보드 전반에서 사용되는 공통 유틸리티 함수들입니다.

제공 기능:
- 상태별 색상 매핑 (status chips, badges)
- 장치 연결 상태 스타일
- 차트 색상 팔레트

Q: 왜 이 함수들을 별도 모듈로 분리했나요?
A: DRY(Don't Repeat Yourself) 원칙 적용.
   여러 컴포넌트에서 동일한 색상/스타일을 사용하므로
   한 곳에서 정의하고 재사용합니다.
=============================================================================
"""

from typing import Dict, Literal


# =============================================================================
# 타입 정의
# Literal: 허용되는 값을 명시적으로 제한
# IDE 자동완성과 타입 검사에 도움
# =============================================================================
StatusVariant = Literal["success", "warning", "destructive", "default", "info"]


def get_status_color(variant: StatusVariant) -> Dict[str, str]:
    """
    상태 variant에 대한 색상 스키마 반환.
    
    status chips, badges, indicators 등에서 일관된 색상 테마를 위해 사용됩니다.
    색상은 엔터프라이즈 대시보드 관례를 따르며 명확한 의미를 전달합니다.
    
    Args:
        variant: 상태 타입
            - 'success': 녹색 (정상, 연결됨)
            - 'warning': 노란색 (경고)
            - 'destructive': 빨간색 (오류, 연결 끊김)
            - 'info': 파란색 (정보)
            - 'default': 회색 (기본)
    
    Returns:
        'bg', 'border', 'text' 색상 hex 값을 담은 딕셔너리
    
    Q: 왜 hex 색상을 사용하나요?
    A: CSS에서 가장 널리 사용되는 형식입니다.
       브라우저 호환성이 가장 좋습니다.
        
    사용 예시:
        >>> colors = get_status_color('success')
        >>> print(colors['bg'])  # '#d1fae5'
    """
    # =========================================================================
    # 색상 팔레트 (Tailwind CSS 기반)
    # - success: green-100/200/800
    # - warning: amber-100/200/800
    # - destructive: red-100/200/800
    # - info: blue-100/200/800
    # - default: slate-100/200/700
    # =========================================================================
    color_map = {
        "success": {
            "bg": "#d1fae5",        # 배경색 (연한 녹색)
            "border": "#a7f3d0",    # 테두리 (중간 녹색)
            "text": "#065f46"       # 텍스트 (진한 녹색)
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
    
    # .get()으로 안전하게 조회, 없으면 default 반환
    return color_map.get(variant, color_map["default"])


def get_device_status_style(connected: bool, warning: bool = False) -> Dict[str, str]:
    """
    장치 연결 상태에 따른 CSS 스타일 반환.
    
    device_grid.py에서 각 장치 박스의 스타일링에 사용됩니다.
    연결 상태에 따라 녹색/노란색/빨간색 배경을 적용합니다.
    
    Args:
        connected: 장치 연결 여부
        warning: 경고 상태 여부 (connected=True일 때만 의미 있음)
    
    Returns:
        CSS 스타일 딕셔너리:
        - backgroundColor: 배경색
        - border: 테두리
        - color: 텍스트 색상
    
    로직:
        - not connected → 빨간색 (destructive)
        - connected + warning → 노란색 (warning)
        - connected + not warning → 녹색 (success)
    
    Q: 왜 inline style을 사용하나요?
    A: Dash에서 동적 스타일링에 가장 직접적인 방법입니다.
       상태가 자주 바뀌므로 CSS 클래스보다 유연합니다.
    """
    if not connected:
        # 빨간색: 연결 안 됨 (destructive)
        return {
            "backgroundColor": "#fee2e2",
            "border": "1px solid #fecaca",
            "color": "#991b1b"
        }
    elif warning:
        # 노란색: 연결됨 + 경고 (warning)
        return {
            "backgroundColor": "#fef3c7",
            "border": "1px solid #fde68a",
            "color": "#92400e"
        }
    else:
        # 녹색: 정상 연결 (success)
        return {
            "backgroundColor": "#d1fae5",
            "border": "1px solid #a7f3d0",
            "color": "#065f46"
        }


def get_chart_colors() -> Dict[str, str]:
    """
    차트 색상 팔레트 반환.
    
    charts.py의 PPS, Jitter, Availability 차트에서 사용됩니다.
    일관된 색상 테마를 유지합니다.
    
    Returns:
        차트 요소별 색상 딕셔너리:
        - primary: PPS 라인 (파란색)
        - secondary: Jitter 라인 (녹색)
        - p95_line: P95 참조선 (주황색)
        - p99_line: P99 참조선 (빨간색)
        - fill_*: 영역 채우기 색상 (투명도 적용)
        - up_segment/down_segment: 가용성 타임라인
        - grid: 그리드 라인
    
    Q: 왜 rgba를 사용하나요?
    A: fill 색상에 투명도(알파값)를 적용하기 위함입니다.
       0.1 = 10% 불투명, 즉 90% 투명합니다.
       영역 차트가 너무 진해지지 않도록 합니다.
    """
    return {
        # 라인 색상
        "primary": "#3b82f6",        # 파란색 - PPS 라인
        "secondary": "#10b981",      # 녹색 - Jitter 라인
        
        # 참조선 색상
        "p95_line": "#f59e0b",       # 주황색 - P95 기준선
        "p99_line": "#ef4444",       # 빨간색 - P99 기준선
        
        # 영역 채우기 색상 (투명도 적용)
        "fill_primary": "rgba(59, 130, 246, 0.1)",   # 연한 파란색
        "fill_secondary": "rgba(16, 185, 129, 0.1)", # 연한 녹색
        
        # 가용성 타임라인 색상
        "up_segment": "#10b981",     # 녹색 - 시스템 UP
        "down_segment": "#ef4444",   # 빨간색 - 시스템 DOWN
        
        # 그리드 색상
        "grid": "#f1f5f9",           # 연한 회색
    }


# =============================================================================
# 미사용 함수 삭제 (2026-01-20)
# 아래 함수들은 parser/icd_parser.py 및 analysis/ 모듈로 이동됨
# - format_percentage(): 직접 f-string 사용으로 대체
# - format_timestamp(): models.py의 to_dict() 메서드에서 직접 처리
# - calculate_availability(): analysis/stats_calculator.py로 이동
# - get_operation_mode_label(): parser/icd_parser.py로 이동
# - get_authority_label(): parser/icd_parser.py로 이동
# - get_driving_state_label(): parser/icd_parser.py로 이동
# - seq_gap_with_rollover(): analysis/stats_calculator.py로 이동
# =============================================================================
