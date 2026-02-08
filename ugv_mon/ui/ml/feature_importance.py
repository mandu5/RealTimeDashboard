"""
기여 특성 차트.

이상 탐지 시 어떤 특성이 가장 많이 기여했는지 시각화합니다.
Z-score 기반으로 각 특성의 정상 범위 이탈 정도를 보여줍니다.
"""

import plotly.graph_objects as go


def create_feature_contribution_chart(
    contributing_features: list[dict],
    max_features: int = 5,
) -> go.Figure:
    """기여 특성 수평 바 차트."""
    if not contributing_features:
        return _create_empty_chart()

    features = contributing_features[:max_features]

    names = [f["name"] for f in features]
    z_scores = [abs(f["z_score"]) for f in features]
    directions = ["+" if f["z_score"] > 0 else "-" for f in features]

    colors = []
    for z in z_scores:
        if z > 3:
            colors.append("#ef4444")
        elif z > 2:
            colors.append("#f97316")
        elif z > 1.5:
            colors.append("#f59e0b")
        else:
            colors.append("#3b82f6")

    fig = go.Figure(go.Bar(
        x=z_scores,
        y=names,
        orientation="h",
        marker_color=colors,
        text=[f"z={d}{z:.1f}" for d, z in zip(directions, z_scores)],
        textposition="outside",
        textfont={"color": "white"},
        hovertemplate="특성: %{y}<br>Z-Score: %{x:.2f}<extra></extra>",
    ))

    fig.update_layout(
        title={
            "text": "이상 기여 특성 (Z-Score)",
            "font": {"size": 14, "color": "white"},
            "x": 0.5,
        },
        xaxis={
            "title": "Z-Score (절대값)",
            "gridcolor": "#374151",
            "zerolinecolor": "#4b5563",
            "range": [0, max(z_scores) * 1.3] if z_scores else [0, 5],
        },
        yaxis={
            "autorange": "reversed",
            "gridcolor": "#374151",
        },
        paper_bgcolor="rgba(17, 24, 39, 1)",
        plot_bgcolor="rgba(17, 24, 39, 0.8)",
        font={"color": "white"},
        height=220,
        margin={"l": 120, "r": 60, "t": 50, "b": 40},
        showlegend=False,
    )

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
        xaxis={
            "title": "Z-Score",
            "range": [0, 5],
            "showgrid": False,
            "showticklabels": False,
        },
        yaxis={
            "title": "",
            "showgrid": False,
            "showticklabels": False,
        },
        paper_bgcolor="rgba(17, 24, 39, 1)",
        plot_bgcolor="rgba(17, 24, 39, 0.8)",
        font={"color": "white"},
        height=220,
        margin={"l": 40, "r": 40, "t": 50, "b": 40},
        annotations=[
            {
                "text": "✅ 현재 모든 특성이 정상 범위입니다",
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "font": {"color": "#22c55e", "size": 16, "family": "Arial"},
            }
        ],
    )
    return fig
