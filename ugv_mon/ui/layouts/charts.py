"""
Chart Components for UGV-MON Dashboard.

Provides Plotly chart builders for:
- PPS time series (packets per second)
- Jitter time series with P95 reference line
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ...styles import get_chart_colors


def create_communication_chart(
    data: list[dict],
    p95: float,
    time_range_seconds: int = 60,
) -> go.Figure:
    """
    Create combined PPS + Jitter time series chart.

    Displays two stacked charts:
    1. Top: Packets per second (PPS) - blue area chart
    2. Bottom: Jitter (ms) - green area chart with P95 reference line

    Args:
        data: List of dictionaries with 'timestamp', 'pps', 'jitter' keys
        p95: Current P95 jitter value (ms)
        time_range_seconds: Time range to display in seconds (default 60)

    Returns:
        Plotly Figure object

    Example:
        >>> data = [
        ...     {"timestamp": "14:32:05", "pps": 1024, "jitter": 1.5},
        ...     ...
        ... ]
        >>> fig = create_communication_chart(data, 2.1, 60)
    """
    colors = get_chart_colors()

    # Filter data based on time range (keep only last N points)
    # Poll interval ~2s → ~0.5 points/sec → 60s ≈ 30 points
    points_per_second = 0.5
    max_points = int(time_range_seconds * points_per_second)
    filtered_data = data[-max_points:] if len(data) > max_points else data

    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("패킷 수신율 (PPS)", "지터 (Jitter, ms)"),
        vertical_spacing=0.15,  # Increased spacing between subplots
        row_heights=[0.5, 0.5],
    )

    # Extract data series from filtered data
    timestamps = [d.get("timestamp", "") for d in filtered_data]
    pps_values = [d.get("pps", 0) for d in filtered_data]
    jitter_values = [d.get("jitter", 0) for d in filtered_data]

    # PPS Chart (top)
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=pps_values,
            mode="lines",
            name="PPS",
            line={"color": colors["primary"], "width": 2},
            fill="tozeroy",
            fillcolor=colors["fill_primary"],
            hovertemplate="PPS: %{y}<br>Time: %{x}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Jitter Chart (bottom)
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=jitter_values,
            mode="lines",
            name="Jitter",
            line={"color": colors["secondary"], "width": 2},
            fill="tozeroy",
            fillcolor=colors["fill_secondary"],
            hovertemplate="Jitter: %{y}ms<br>Time: %{x}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # P95 reference line
    fig.add_hline(
        y=p95,
        line_dash="dash",
        line_color=colors["p95_line"],
        annotation_text=f"P95: {p95}ms",
        annotation_position="right",
        row=2,
        col=1,
    )

    # Update axes styling
    n_ticks = 5

    x_axis_style = {"showgrid": True, "gridwidth": 1, "gridcolor": colors["grid"], "nticks": n_ticks, "tickformat": "%H:%M:%S", "tickangle": 0, "title": None}
    y_axis_style = {"showgrid": True, "gridwidth": 1, "gridcolor": colors["grid"], "rangemode": "normal"}

    for row in [1, 2]:
        fig.update_xaxes(**x_axis_style, row=row, col=1)
        fig.update_yaxes(**y_axis_style, row=row, col=1)

    # Layout configuration
    fig.update_layout(
        height=400,
        margin={"l": 40, "r": 40, "t": 40, "b": 40},
        plot_bgcolor="white",
        paper_bgcolor="white",
        font={"family": "Inter, sans-serif", "size": 11},
        showlegend=False,
        hovermode="x unified",
        dragmode=False,
    )

    return fig


# =============================================================================
# 미사용 함수 삭제 (2026-01-20)
# - create_pps_chart(): create_communication_chart()에 통합됨
# - create_jitter_chart(): create_communication_chart()에 통합됨
# =============================================================================
