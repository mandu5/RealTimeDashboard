"""
이상 점수 타임라인 차트.

시간 축에 따른 이상 점수 추이와 임계값을 함께 표시합니다.
이상 구간은 빨간색으로 하이라이트됩니다.
"""

from typing import Optional

import plotly.graph_objects as go


def create_anomaly_timeline(
    scores: list[dict],
    threshold: float = -0.3,
) -> go.Figure:
    """이상 점수 시계열 차트.

    - 이상 점수 라인 (보라색)
    - 임계값 점선 (빨간색)
    - 이상 구간 빨간색 하이라이트

    Args:
        scores: [{\"timestamp\": str, \"score\": float}, ...]
        threshold: 이상 판정 임계값 (기본 -0.3)

    Returns:
        go.Figure: Plotly 시계열 Figure

    Example:
        >>> scores = [{\"timestamp\": \"12:00:00\", \"score\": -0.1}, ...]
        >>> fig = create_anomaly_timeline(scores, threshold=-0.3)
        >>> fig.show()
    """
    if not scores:
        return _create_empty_timeline()

    timestamps = [s["timestamp"] for s in scores]
    values = [s["score"] for s in scores]

    fig = go.Figure()

    # 이상 점수 라인 (면적 채우기)
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=values,
        mode="lines",
        name="Anomaly Score",
        line={"color": "#8b5cf6", "width": 2},
        fill="tozeroy",
        fillcolor="rgba(139, 92, 246, 0.15)",
        hovertemplate="시간: %{x}<br>점수: %{y:.3f}<extra></extra>",
    ))

    # 임계값 라인
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color="#ef4444",
        line_width=2,
        annotation_text=f"Threshold ({threshold})",
        annotation_position="top right",
        annotation_font_color="#ef4444",
    )

    # 이상 구간 하이라이트
    anomaly_regions = _find_anomaly_regions(timestamps, values, threshold)
    for start, end in anomaly_regions:
        fig.add_vrect(
            x0=start,
            x1=end,
            fillcolor="rgba(239, 68, 68, 0.2)",
            line_width=0,
            layer="below",
        )

    # 레이아웃
    fig.update_layout(
        title={
            "text": "Anomaly Score Timeline",
            "font": {"size": 14, "color": "white"},
            "x": 0.5,
        },
        xaxis={
            "title": "시간",
            "gridcolor": "#374151",
            "zerolinecolor": "#4b5563",
            "nticks": 10,  # 최대 10개 레이블만 표시
            "tickangle": -45,  # 45도 기울임
        },
        yaxis={
            "title": "이상 점수",
            "gridcolor": "#374151",
            "zerolinecolor": "#4b5563",
            "range": [-1, 0.5],
        },
        paper_bgcolor="rgba(17, 24, 39, 1)",
        plot_bgcolor="rgba(17, 24, 39, 0.8)",
        font={"color": "white", "size": 10},
        height=280,
        margin={"l": 50, "r": 20, "t": 50, "b": 70},  # 하단 여백 증가
        showlegend=False,
    )

    return fig


def _find_anomaly_regions(
    timestamps: list[str],
    scores: list[float],
    threshold: float,
) -> list[tuple[str, str]]:
    """연속된 이상 구간을 찾아 (start, end) 튜플 리스트로 반환."""
    if not timestamps or not scores:
        return []

    regions = []
    in_anomaly = False
    start: Optional[str] = None

    for ts, score in zip(timestamps, scores):
        if score < threshold and not in_anomaly:
            start = ts
            in_anomaly = True
        elif score >= threshold and in_anomaly:
            if start is not None:
                regions.append((start, ts))
            in_anomaly = False
            start = None

    # 마지막 구간이 열려있으면 닫기
    if in_anomaly and start is not None:
        regions.append((start, timestamps[-1]))

    return regions


def _create_empty_timeline() -> go.Figure:
    """데이터 없을 때 빈 타임라인."""
    fig = go.Figure()
    fig.update_layout(
        title="Anomaly Score Timeline (데이터 없음)",
        xaxis={"title": "시간", "nticks": 10},
        yaxis={"title": "이상 점수", "range": [-1, 0.5]},
        paper_bgcolor="rgba(17, 24, 39, 1)",
        plot_bgcolor="rgba(17, 24, 39, 0.8)",
        font={"color": "white", "size": 10},
        height=280,
        margin={"l": 50, "r": 20, "t": 50, "b": 70},
        annotations=[
            {
                "text": "ML 모델 학습 후 표시됩니다",
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "font": {"color": "#9ca3af"},
            }
        ],
    )
    return fig


def create_confidence_gauge(confidence: float) -> go.Figure:
    """이상 탐지 신뢰도 게이지 차트.

    Args:
        confidence: 신뢰도 (0 ~ 1)

    Returns:
        반원형 게이지 차트
    """
    # 색상 결정
    if confidence < 0.3:
        color = "#22c55e"  # 녹색 (정상)
    elif confidence < 0.7:
        color = "#f59e0b"  # 노란색 (주의)
    else:
        color = "#ef4444"  # 빨간색 (이상)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=confidence * 100,
        number={"suffix": "%", "font": {"color": "white"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "white"},
            "bar": {"color": color},
            "bgcolor": "rgba(75, 85, 99, 0.5)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": "rgba(34, 197, 94, 0.3)"},
                {"range": [30, 70], "color": "rgba(245, 158, 11, 0.3)"},
                {"range": [70, 100], "color": "rgba(239, 68, 68, 0.3)"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.75,
                "value": confidence * 100,
            },
        },
        title={"text": "이상 신뢰도", "font": {"color": "white", "size": 14}},
    ))

    fig.update_layout(
        paper_bgcolor="rgba(17, 24, 39, 1)",
        font={"color": "white"},
        height=200,
        margin={"l": 30, "r": 30, "t": 50, "b": 20},
    )

    return fig
