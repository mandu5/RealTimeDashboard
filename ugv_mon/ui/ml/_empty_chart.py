"""ML 차트용 빈 Figure 공통 생성.

데이터 부재 시 표시할 placeholder 차트를 제공합니다.
"""

from typing import Optional

import plotly.graph_objects as go

# ML 차트 높이 상수 (3D, 타임라인, 기여 특성)
ML_CHART_HEIGHT_3D = 450
ML_CHART_HEIGHT_TIMELINE = 280
ML_CHART_HEIGHT_FEATURE = 220


def create_empty_ml_chart(
    title: str,
    message: str,
    layout_overrides: Optional[dict] = None,
) -> go.Figure:
    """빈 ML 차트 Figure 생성.

    Args:
        title: 차트 제목
        message: 중앙 표시 메시지 (annotation)
        layout_overrides: 추가/덮어쓸 레이아웃 속성 (height, margin, scene 등)

    Returns:
        go.Figure: 빈 상태 placeholder Figure
    """
    fig = go.Figure()
    base = {
        "paper_bgcolor": "rgba(17, 24, 39, 1)",
        "plot_bgcolor": "rgba(17, 24, 39, 0.8)",
        "font": {"color": "white"},
        "annotations": [
            {
                "text": message,
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "font": {"color": "#9ca3af"},
            }
        ],
    }
    overrides = layout_overrides or {}
    layout = {**base, **overrides}
    fig.update_layout(title=title, **layout)
    return fig
