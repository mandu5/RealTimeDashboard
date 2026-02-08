"""
기여 특성 차트.

이상 탐지 시 어떤 특성이 가장 많이 기여했는지 시각화합니다.
Z-score 기반으로 각 특성의 정상 범위 이탈 정도를 보여줍니다.
"""

import plotly.graph_objects as go
from typing import List, Dict


def create_feature_contribution_chart(
    contributing_features: List[Dict],
    max_features: int = 5,
) -> go.Figure:
    """기여 특성 수평 바 차트.
    
    Z-score 기반으로 각 특성이 이상에 얼마나 기여했는지 보여줍니다.
    
    Args:
        contributing_features: [{"name": str, "z_score": float}, ...]
        max_features: 표시할 최대 특성 수 (기본 5)
        
    Returns:
        수평 바 차트 Figure
        
    Example:
        >>> features = [
        ...     {"name": "jitter_volatility", "z_score": 3.2},
        ...     {"name": "pps_trend", "z_score": -2.5},
        ... ]
        >>> fig = create_feature_contribution_chart(features)
        >>> fig.show()
    """
    if not contributing_features:
        return _create_empty_chart()
    
    # 상위 N개만 사용
    features = contributing_features[:max_features]
    
    names = [f["name"] for f in features]
    z_scores = [abs(f["z_score"]) for f in features]
    directions = ["+" if f["z_score"] > 0 else "-" for f in features]
    
    # 색상 결정 (Z-score 크기에 따라)
    colors = []
    for z in z_scores:
        if z > 3:
            colors.append("#ef4444")  # 빨간색 (심각)
        elif z > 2:
            colors.append("#f97316")  # 주황색 (경고)
        elif z > 1.5:
            colors.append("#f59e0b")  # 노란색 (주의)
        else:
            colors.append("#3b82f6")  # 파란색 (정상)
    
    fig = go.Figure(go.Bar(
        x=z_scores,
        y=names,
        orientation="h",
        marker_color=colors,
        text=[f"z={d}{z:.1f}" for d, z in zip(directions, z_scores)],
        textposition="outside",
        textfont=dict(color="white"),
        hovertemplate="특성: %{y}<br>Z-Score: %{x:.2f}<extra></extra>",
    ))
    
    # 레이아웃
    fig.update_layout(
        title=dict(
            text="이상 기여 특성 (Z-Score)",
            font=dict(size=14, color="white"),
            x=0.5,
        ),
        xaxis=dict(
            title="Z-Score (절대값)",
            gridcolor="#374151",
            zerolinecolor="#4b5563",
            range=[0, max(z_scores) * 1.3] if z_scores else [0, 5],
        ),
        yaxis=dict(
            autorange="reversed",  # 가장 큰 값이 위에
            gridcolor="#374151",
        ),
        paper_bgcolor="rgba(17, 24, 39, 1)",
        plot_bgcolor="rgba(17, 24, 39, 0.8)",
        font=dict(color="white"),
        height=220,
        margin=dict(l=120, r=60, t=50, b=40),
        showlegend=False,
    )
    
    # Z-score 임계값 표시 (2.0)
    fig.add_vline(
        x=2.0,
        line_dash="dash",
        line_color="#f59e0b",
        line_width=1,
        annotation_text="2σ",
        annotation_position="top",
        annotation_font_color="#f59e0b",
    )
    
    return fig


def _create_empty_chart() -> go.Figure:
    """기여 특성 없을 때 빈 차트."""
    fig = go.Figure()
    fig.update_layout(
        title="이상 기여 특성 (정상 상태)",
        xaxis=dict(
            title="Z-Score", 
            range=[0, 5],
            showgrid=False,  # 그리드 숨김
            showticklabels=False,  # 레이블 숨김
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            showticklabels=False,
        ),
        paper_bgcolor="rgba(17, 24, 39, 1)",
        plot_bgcolor="rgba(17, 24, 39, 0.8)",
        font=dict(color="white"),
        height=220,
        margin=dict(l=40, r=40, t=50, b=40),
        annotations=[
            dict(
                text="✅ 현재 모든 특성이 정상 범위입니다",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                font=dict(color="#22c55e", size=16, family="Arial"),
            )
        ],
    )
    return fig


def create_feature_radar_chart(features: Dict[str, float]) -> go.Figure:
    """특성 레이더 차트 (스파이더 차트).
    
    모든 특성을 한눈에 비교할 수 있는 레이더 형태입니다.
    정상 범위는 원 안쪽, 이상은 바깥쪽으로 표시됩니다.
    
    Args:
        features: {"feature_name": z_score, ...}
        
    Returns:
        레이더 차트 Figure
    """
    if not features:
        return _create_empty_chart()
    
    names = list(features.keys())
    values = [abs(v) for v in features.values()]
    
    # 닫힌 다각형을 위해 첫 값 반복
    names_closed = names + [names[0]]
    values_closed = values + [values[0]]
    
    fig = go.Figure()
    
    # 실제 값
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=names_closed,
        fill="toself",
        fillcolor="rgba(139, 92, 246, 0.3)",
        line=dict(color="#8b5cf6", width=2),
        name="현재 상태",
    ))
    
    # 정상 범위 (2σ)
    fig.add_trace(go.Scatterpolar(
        r=[2.0] * len(names_closed),
        theta=names_closed,
        fill="none",
        line=dict(color="#f59e0b", width=1, dash="dash"),
        name="정상 범위 (2σ)",
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(values) * 1.2] if values else [0, 5],
                gridcolor="#374151",
            ),
            angularaxis=dict(gridcolor="#374151"),
            bgcolor="rgba(17, 24, 39, 0.8)",
        ),
        paper_bgcolor="rgba(17, 24, 39, 1)",
        font=dict(color="white"),
        title=dict(
            text="특성 레이더 차트",
            font=dict(size=14, color="white"),
            x=0.5,
        ),
        height=350,
        margin=dict(l=60, r=60, t=60, b=40),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
        ),
    )
    
    return fig
