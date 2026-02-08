"""
3D 이상 탐지 산점도.

(지터, PPS, 손실률) 3축 공간에서 정상/이상 패턴을 시각적으로 분리합니다.
Plotly WebGL을 활용하여 대량 데이터도 부드럽게 렌더링합니다.

면접 어필 포인트:
    "3D 시각화를 통해 단일 변수 임계값으로는 발견할 수 없는
    다변량 이상 패턴을 직관적으로 보여줄 수 있습니다."
"""

from typing import Optional

import plotly.graph_objects as go


def create_anomaly_3d_scatter(
    records: list[dict],
    anomaly_scores: Optional[list[float]] = None,
    threshold: float = -0.3,
) -> go.Figure:
    """3D 이상 탐지 산점도 생성.

    정상 데이터는 파란색, 이상 데이터는 빨간색으로 표시.
    마커 크기는 이상 점수의 심각도에 비례합니다.

    Args:
        records: 레코드 리스트 (각 레코드는 jitter, pps, loss_rate 포함)
        anomaly_scores: 각 레코드의 이상 점수 (-1 ~ 0, 낮을수록 이상)
        threshold: 이상 판정 임계값 (기본 -0.3)

    Returns:
        go.Figure: Plotly 3D 산점도 Figure

    Example:
        >>> records = [{"jitter_current": 2.5, "pps": 100, "loss_rate": 0.5, "timestamp": "12:00:00"}, ...]
        >>> scores = [-0.1, -0.4, -0.2, ...]  # 이상 점수
        >>> fig = create_anomaly_3d_scatter(records, scores)
        >>> fig.show()
    """
    if not records:
        return _create_empty_figure()

    # 데이터 추출
    jitters = [r.get("jitter_current", 0) for r in records]
    pps_values = [r.get("pps", 0) for r in records]
    loss_rates = [r.get("loss_rate", 0) for r in records]
    timestamps = [r.get("timestamp", "") for r in records]

    # 이상 점수가 없으면 기본값 사용
    if anomaly_scores is None:
        anomaly_scores = [0.0] * len(records)

    # 색상: 이상 점수 기준 (낮을수록 빨간색)
    colors = _scores_to_colors(anomaly_scores, threshold)

    # 마커 크기: 이상일수록 큼 (최소 5, 최대 15)
    sizes = [
        max(5, min(15, 5 + abs(s) * 20)) if s < threshold else 5
        for s in anomaly_scores
    ]

    fig = go.Figure(data=[go.Scatter3d(
        x=jitters,
        y=pps_values,
        z=loss_rates,
        mode="markers",
        marker={
            "size": sizes,
            "color": colors,
            "opacity": 0.8,
            "line": {"width": 0.5, "color": "white"},
        },
        text=[
            f"시간: {ts}<br>"
            f"지터: {j:.2f}ms<br>"
            f"PPS: {p}<br>"
            f"손실률: {l:.2f}%<br>"
            f"이상 점수: {s:.3f}"
            for ts, j, p, l, s in zip(
                timestamps, jitters, pps_values, loss_rates, anomaly_scores
            )
        ],
        hoverinfo="text",
        name="데이터 포인트",
    )])

    # 레이아웃 설정
    fig.update_layout(
        scene={
            "xaxis": {"title": "지터 (ms)", "gridcolor": "#444", "zerolinecolor": "#666"},
            "yaxis": {"title": "PPS", "gridcolor": "#444", "zerolinecolor": "#666"},
            "zaxis": {"title": "손실률 (%)", "gridcolor": "#444", "zerolinecolor": "#666"},
            "bgcolor": "rgba(17, 24, 39, 0.8)",  # 다크 배경
        },
        paper_bgcolor="rgba(17, 24, 39, 1)",
        font={"color": "white"},
        title={
            "text": "3D Anomaly Detection View",
            "font": {"size": 16, "color": "white"},
            "x": 0.5,
        },
        height=450,
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
        showlegend=False,
    )

    # 카메라 앵글 설정 (45도 기울기)
    fig.update_layout(
        scene_camera={
            "up": {"x": 0, "y": 0, "z": 1},
            "center": {"x": 0, "y": 0, "z": -0.1},
            "eye": {"x": 1.5, "y": 1.5, "z": 1.2},
        }
    )

    return fig


def _scores_to_colors(
    scores: list[float],
    threshold: float,
) -> list[str]:
    """이상 점수를 색상으로 변환.

    정상: 파란색 계열 (#3b82f6)
    이상: 빨간색 계열 (#ef4444)
    경계: 노란색 계열 (#f59e0b)
    """
    colors = []
    for s in scores:
        if s < threshold:
            # 이상 (빨간색)
            colors.append("#ef4444")
        elif s < threshold + 0.1:
            # 경계 (노란색)
            colors.append("#f59e0b")
        else:
            # 정상 (파란색)
            colors.append("#3b82f6")
    return colors


def _create_empty_figure() -> go.Figure:
    """데이터 없을 때 빈 Figure 반환."""
    fig = go.Figure()
    fig.update_layout(
        scene={
            "xaxis": {"title": "지터 (ms)"},
            "yaxis": {"title": "PPS"},
            "zaxis": {"title": "손실률 (%)"},
        },
        title="3D Anomaly Detection View (데이터 없음)",
        height=450,
        annotations=[
            {
                "text": "데이터가 충분히 수집되면 표시됩니다",
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
            }
        ],
    )
    return fig


def create_anomaly_3d_scatter_animated(
    records_history: list[list[dict]],
    scores_history: list[list[float]],
    frame_duration: int = 500,
) -> go.Figure:
    """시간에 따른 3D 산점도 애니메이션.

    시간 경과에 따라 이상 패턴이 어떻게 변화하는지 보여줍니다.

    Args:
        records_history: 시간별 레코드 리스트의 리스트
        scores_history: 시간별 이상 점수 리스트의 리스트
        frame_duration: 프레임 간 간격 (ms)

    Returns:
        애니메이션이 포함된 Plotly Figure
    """
    if not records_history:
        return _create_empty_figure()

    # 첫 프레임으로 기본 Figure 생성
    fig = create_anomaly_3d_scatter(records_history[0], scores_history[0] if scores_history else None)

    # 프레임 추가
    frames = []
    for i, (records, scores) in enumerate(zip(records_history, scores_history or [[] for _ in records_history])):
        jitters = [r.get("jitter_current", 0) for r in records]
        pps_values = [r.get("pps", 0) for r in records]
        loss_rates = [r.get("loss_rate", 0) for r in records]
        colors = _scores_to_colors(scores, -0.3) if scores else ["#3b82f6"] * len(records)

        frame = go.Frame(
            data=[go.Scatter3d(
                x=jitters,
                y=pps_values,
                z=loss_rates,
                mode="markers",
                marker={"size": 6, "color": colors, "opacity": 0.8},
            )],
            name=str(i),
        )
        frames.append(frame)

    fig.frames = frames

    # 애니메이션 버튼 추가
    fig.update_layout(
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "y": 0,
                "x": 0.1,
                "buttons": [
                    {
                        "label": "▶ Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": frame_duration, "redraw": True},
                                "fromcurrent": True,
                            },
                        ],
                    },
                    {
                        "label": "⏸ Pause",
                        "method": "animate",
                        "args": [
                            [None],
                            {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"},
                        ],
                    },
                ],
            }
        ],
    )

    return fig
