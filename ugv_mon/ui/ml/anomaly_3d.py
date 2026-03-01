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

from ._empty_chart import ML_CHART_HEIGHT_3D, create_empty_ml_chart

# 축 공통 스타일
_AXIS_STYLE: dict = {
    "gridcolor": "rgba(75, 85, 99, 0.4)",
    "zerolinecolor": "rgba(107, 114, 128, 0.5)",
    "backgroundcolor": "rgba(17, 24, 39, 0.6)",
    "showbackground": True,
    "tickfont": {"size": 10, "color": "#9ca3af"},
    "title_font": {"size": 11, "color": "#d1d5db"},
}


def create_anomaly_3d_scatter(
    records: list[dict],
    anomaly_scores: Optional[list[float]] = None,
    threshold: float = -0.3,
) -> go.Figure:
    """3D 이상 탐지 산점도 생성.

    정상/경고/이상 데이터를 별도 트레이스로 분리하여 범례를 표시합니다.
    연속 컬러스케일로 이상 심각도를 시각적으로 구분하고,
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
        return create_empty_ml_chart(
            "3D Anomaly Detection View (데이터 없음)",
            "데이터가 충분히 수집되면 표시됩니다",
            {
                "scene": {
                    "xaxis": {"title": "지터 (ms)", **_AXIS_STYLE},
                    "yaxis": {"title": "PPS", **_AXIS_STYLE},
                    "zaxis": {"title": "손실률 (%)", **_AXIS_STYLE},
                    "bgcolor": "rgba(10, 15, 28, 1)",
                },
                "height": ML_CHART_HEIGHT_3D,
            },
        )

    # 데이터 추출
    jitters = [r.get("jitter_current", 0) for r in records]
    pps_values = [r.get("pps", 0) for r in records]
    loss_rates = [r.get("loss_rate", 0) for r in records]
    timestamps = [r.get("timestamp", "") for r in records]

    # 이상 점수가 없으면 기본값 사용
    if anomaly_scores is None:
        anomaly_scores = [0.0] * len(records)

    # 정상 / 경고 / 이상 데이터 분류
    normal, warning, anomaly = _split_by_status(
        jitters, pps_values, loss_rates, timestamps, anomaly_scores, threshold,
    )

    fig = go.Figure()

    # --- 정상 트레이스 (파란색 계열) ---
    if normal["x"]:
        fig.add_trace(go.Scatter3d(
            x=normal["x"], y=normal["y"], z=normal["z"],
            mode="markers",
            marker={
                "size": normal["sizes"],
                "color": normal["scores"],
                "colorscale": [[0, "#1e40af"], [1, "#60a5fa"]],
                "cmin": threshold,
                "cmax": 0.1,
                "opacity": 0.7,
                "line": {"width": 0.3, "color": "rgba(255,255,255,0.2)"},
            },
            text=normal["texts"],
            hoverinfo="text",
            name=f"Normal ({len(normal['x'])})",
            legendgroup="normal",
        ))

    # --- 경고 트레이스 (노란색 계열) ---
    if warning["x"]:
        fig.add_trace(go.Scatter3d(
            x=warning["x"], y=warning["y"], z=warning["z"],
            mode="markers",
            marker={
                "size": warning["sizes"],
                "color": "#fbbf24",
                "opacity": 0.85,
                "symbol": "diamond",
                "line": {"width": 0.5, "color": "rgba(251, 191, 36, 0.6)"},
            },
            text=warning["texts"],
            hoverinfo="text",
            name=f"Warning ({len(warning['x'])})",
            legendgroup="warning",
        ))

    # --- 이상 트레이스 (빨간색 계열, 글로우 효과) ---
    if anomaly["x"]:
        fig.add_trace(go.Scatter3d(
            x=anomaly["x"], y=anomaly["y"], z=anomaly["z"],
            mode="markers",
            marker={
                "size": anomaly["sizes"],
                "color": anomaly["scores"],
                "colorscale": [[0, "#dc2626"], [0.5, "#ef4444"], [1, "#fca5a5"]],
                "cmin": -1.0,
                "cmax": threshold,
                "opacity": 0.95,
                "symbol": "x",
                "line": {"width": 1, "color": "rgba(239, 68, 68, 0.8)"},
            },
            text=anomaly["texts"],
            hoverinfo="text",
            name=f"Anomaly ({len(anomaly['x'])})",
            legendgroup="anomaly",
        ))

    # --- 레이아웃 ---
    n_anomaly = len(anomaly["x"])
    n_total = len(records)
    anomaly_pct = (n_anomaly / n_total * 100) if n_total else 0

    fig.update_layout(
        uirevision="ml-3d-scatter",
        scene={
            "uirevision": "ml-3d-scene",
            "xaxis": {"title": "지터 (ms)", **_AXIS_STYLE},
            "yaxis": {"title": "PPS", **_AXIS_STYLE},
            "zaxis": {"title": "손실률 (%)", **_AXIS_STYLE},
            "bgcolor": "rgba(10, 15, 28, 1)",
            "aspectmode": "cube",
        },
        paper_bgcolor="rgba(17, 24, 39, 1)",
        font={"color": "#e5e7eb", "size": 11},
        title={
            "text": (
                '<span style="font-size:15px;font-weight:600;">3D Anomaly Detection View</span>'
                f'<br><span style="font-size:11px;color:#9ca3af;">'
                f"Total {n_total} pts  |  Anomaly {n_anomaly} ({anomaly_pct:.1f}%)"
                f"  |  Threshold {threshold:.2f}</span>"
            ),
            "x": 0.5,
            "xanchor": "center",
        },
        height=ML_CHART_HEIGHT_3D,
        margin={"l": 0, "r": 0, "t": 70, "b": 10},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.02,
            "xanchor": "center",
            "x": 0.5,
            "bgcolor": "rgba(17, 24, 39, 0.7)",
            "bordercolor": "rgba(75, 85, 99, 0.5)",
            "borderwidth": 1,
            "font": {"size": 11, "color": "#d1d5db"},
            "itemsizing": "constant",
        },
        showlegend=True,
    )

    return fig


def _split_by_status(
    jitters: list[float],
    pps_values: list[float],
    loss_rates: list[float],
    timestamps: list[str],
    scores: list[float],
    threshold: float,
) -> tuple[dict, dict, dict]:
    """데이터를 정상/경고/이상으로 분류하여 트레이스별 데이터 반환."""
    groups: dict[str, dict] = {
        k: {"x": [], "y": [], "z": [], "texts": [], "sizes": [], "scores": []}
        for k in ("normal", "warning", "anomaly")
    }
    warn_upper = threshold + 0.1

    for j, p, l, ts, s in zip(jitters, pps_values, loss_rates, timestamps, scores):
        text = (
            f"<b>시간:</b> {ts}<br>"
            f"<b>지터:</b> {j:.2f} ms<br>"
            f"<b>PPS:</b> {p}<br>"
            f"<b>손실률:</b> {l:.2f}%<br>"
            f"<b>이상 점수:</b> {s:.3f}"
        )
        if s < threshold:
            g = groups["anomaly"]
            size = max(7, min(18, 7 + abs(s) * 22))
        elif s < warn_upper:
            g = groups["warning"]
            size = 6
        else:
            g = groups["normal"]
            size = 4
        g["x"].append(j)
        g["y"].append(p)
        g["z"].append(l)
        g["texts"].append(text)
        g["sizes"].append(size)
        g["scores"].append(s)

    return groups["normal"], groups["warning"], groups["anomaly"]


