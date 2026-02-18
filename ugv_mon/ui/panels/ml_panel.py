"""ML 이상 탐지 패널 — 3D 산점도 / 타임라인 / 기여 특성."""

import dash_mantine_components as dmc
from dash import dcc, html

from ...styles import PANEL_TITLE, flex_row, indicator_bar
from ._common import panel_header


def create_ml_analysis_panel(data: dict) -> dmc.Card:
    """ML 이상 탐지 분석 패널.

    3D 산점도, 타임라인, 기여 특성을 표시합니다.
    모델이 준비되지 않았으면 로딩 상태를 표시합니다.
    """
    from ..layouts.ml_charts import (
        create_anomaly_3d_scatter,
        create_anomaly_timeline,
        create_confidence_gauge,
        create_feature_contribution_chart,
    )

    ml_data = data.get("ml", {})
    model_status = ml_data.get("model_status", "not_ready")

    if model_status == "not_ready":
        return _ml_loading_card()

    is_anomaly = ml_data.get("is_anomaly", False)
    confidence = ml_data.get("confidence", 0)
    threshold = ml_data.get("threshold", -0.3)
    contributing_features = ml_data.get("contributing_features", [])
    records = ml_data.get("records", [])
    score_history = ml_data.get("score_history", [])
    anomaly_scores = [r.get("anomaly_score", 0) for r in records] if records else []

    return dmc.Card(
        children=[
            _ml_header(is_anomaly, confidence),
            _scatter_and_gauge(records, anomaly_scores, threshold, confidence,
                               create_anomaly_3d_scatter, create_confidence_gauge),
            _timeline_and_features(score_history, threshold, contributing_features,
                                   create_anomaly_timeline, create_feature_contribution_chart),
        ],
        withBorder=True, p="lg", radius="md",
    )


def _ml_loading_card() -> dmc.Card:
    """모델 학습 대기 중 카드."""
    return dmc.Card(
        children=[
            panel_header("ML 이상 탐지"),
            html.Div(
                children=[
                    dmc.Loader(size="lg", color="blue"),
                    dmc.Text("ML 모델 학습 대기 중...", size="lg", c="dimmed",
                             style={"marginTop": "16px"}),
                    dmc.Text("데이터 수집 후 자동 시작됩니다.", size="sm", c="dimmed",
                             style={"marginTop": "8px"}),
                ],
                style={
                    "display": "flex", "flexDirection": "column",
                    "alignItems": "center", "justifyContent": "center", "height": "300px",
                },
            ),
        ],
        withBorder=True, p="lg", radius="md",
    )


def _ml_header(is_anomaly: bool, confidence: float) -> html.Div:
    """ML 패널 헤더 (타이틀 + 상태 배지 + 신뢰도)."""
    return html.Div(
        children=[
            html.Div(
                children=[
                    html.Div(style=indicator_bar()),
                    html.Span("ML 이상 탐지", style=PANEL_TITLE),
                    dmc.Badge(
                        "이상 감지" if is_anomaly else "정상",
                        color="red" if is_anomaly else "green",
                        size="lg",
                    ),
                ],
                style=flex_row("12px"),
            ),
            dmc.Text(f"신뢰도: {confidence:.0%}", size="sm", c="dimmed"),
        ],
        style={
            "display": "flex", "justifyContent": "space-between",
            "alignItems": "center", "marginBottom": "16px",
        },
    )


def _scatter_and_gauge(records, anomaly_scores, threshold, confidence,
                       create_scatter, create_gauge) -> html.Div:
    """3D 산점도 + 신뢰도 게이지 행."""
    return html.Div(
        children=[
            html.Div(
                dcc.Graph(
                    id="ml-3d-scatter",
                    figure=create_scatter(records, anomaly_scores, threshold),
                    config={"displayModeBar": False},
                    style={"height": "350px"},
                ),
                style={"flex": "2"},
            ),
            html.Div(
                dcc.Graph(
                    id="ml-confidence-gauge",
                    figure=create_gauge(confidence),
                    config={"displayModeBar": False},
                    style={"height": "180px"},
                ),
                style={"flex": "1"},
            ),
        ],
        style={"display": "flex", "gap": "16px"},
    )


def _timeline_and_features(score_history, threshold, contributing_features,
                            create_timeline, create_features) -> html.Div:
    """타임라인 + 기여 특성 행."""
    return html.Div(
        children=[
            html.Div(
                dcc.Graph(
                    id="ml-anomaly-timeline",
                    figure=create_timeline(score_history, threshold),
                    config={"displayModeBar": False},
                    style={"height": "250px"},
                ),
                style={"flex": "2"},
            ),
            html.Div(
                dcc.Graph(
                    id="ml-feature-contribution",
                    figure=create_features(contributing_features),
                    config={"displayModeBar": False},
                    style={"height": "200px"},
                ),
                style={"flex": "1"},
            ),
        ],
        style={"display": "flex", "gap": "16px", "marginTop": "24px"},
    )
