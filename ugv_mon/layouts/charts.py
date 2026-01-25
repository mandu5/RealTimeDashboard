"""
Chart Components for UGV-MON Dashboard.

Provides Plotly chart builders for:
- PPS time series (packets per second)
- Jitter time series with P95/P99 reference lines
- Availability timeline (up/down segments)
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List

from ..styles import get_chart_colors
from ..config import config


def create_communication_chart(
    data: List[Dict],
    p95: float,
    p99: float,
    time_range_seconds: int = 60
) -> go.Figure:
    """
    Create combined PPS + Jitter time series chart.
    
    Displays two stacked charts:
    1. Top: Packets per second (PPS) - blue area chart
    2. Bottom: Jitter (ms) - green area chart with P95/P99 reference lines
    
    Args:
        data: List of dictionaries with 'timestamp', 'pps', 'jitter' keys
        p95: Current P95 jitter value (ms)
        p99: Current P99 jitter value (ms)
        time_range_seconds: Time range to display in seconds (30, 60, or 300)
        
    Returns:
        Plotly Figure object
        
    Example:
        >>> data = [
        ...     {"timestamp": "14:32:05", "pps": 1024, "jitter": 1.5},
        ...     ...
        ... ]
        >>> fig = create_communication_chart(data, 2.1, 2.4, 60)
    """
    colors = get_chart_colors()
    
    # Filter data based on time range (keep only last N points)
    # Assuming data points come every 1-2 seconds, calculate how many points to show
    # Average poll interval is ~2 seconds, so for 30s we need ~15 points, 60s ~30 points, 300s ~150 points
    points_per_second = 0.5  # Approximate: 1 point per 2 seconds
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
            line=dict(color=colors["primary"], width=2),
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
            line=dict(color=colors["secondary"], width=2),
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
    
    # P99 reference line
    fig.add_hline(
        y=p99,
        line_dash="dash",
        line_color=colors["p99_line"],
        annotation_text=f"P99: {p99}ms",
        annotation_position="right",
        row=2,
        col=1,
    )
    
    # Update axes styling
    # X-axis: 시간 레이블 개선 - 데이터 길이에 따라 동적으로 조정
    # Calculate appropriate number of ticks based on time range
    if time_range_seconds <= 30:
        n_ticks = 4  # 30초: 4개 틱
    elif time_range_seconds <= 60:
        n_ticks = 5  # 1분: 5개 틱
    else:
        n_ticks = 6  # 5분: 6개 틱
    
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=colors["grid"],
        nticks=n_ticks,
        tickformat="%H:%M:%S",
        tickangle=0,
        title=None,  # Remove X-axis title to save space
        row=1,
        col=1,
    )
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=colors["grid"],
        nticks=n_ticks,
        tickformat="%H:%M:%S",
        tickangle=0,
        title=None,  # Remove X-axis title to save space
        row=2,
        col=1,
    )
    
    # Y-axis: 자동 스케일링 적용
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=colors["grid"],
        rangemode="normal",  # 자동 스케일링
        row=1,
        col=1,
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=colors["grid"],
        rangemode="normal",  # 자동 스케일링
        row=2,
        col=1,
    )
    
    # Layout configuration
    fig.update_layout(
        height=400,
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=11),
        showlegend=False,
        hovermode="x unified",
        dragmode=False,
    )
    
    return fig


def create_availability_timeline(
    segments: List[Dict],
    duration: int = None
) -> go.Figure:
    """
    Create availability timeline visualization.
    
    Displays up/down segments as colored horizontal bars:
    - Green: System up (available)
    - Red: System down (unavailable)
    
    Args:
        segments: List of segment dictionaries with:
            - start: Start time in seconds
            - end: End time in seconds
            - status: 'up' or 'down'
        duration: Total timeline duration in seconds (default: from config)
        
    Returns:
        Plotly Figure object
        
    Example:
        >>> segments = [
        ...     {"start": 0, "end": 2700, "status": "up"},
        ...     {"start": 2700, "end": 2850, "status": "down"},
        ...     {"start": 2850, "end": 3600, "status": "up"},
        ... ]
        >>> fig = create_availability_timeline(segments)
    """
    if duration is None:
        duration = config.ui.timeline_duration_sec
        
    colors = get_chart_colors()
    
    fig = go.Figure()
    
    # Filter and validate segments
    valid_segments = []
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        # Only add segments with valid duration
        if end > start and end > 0:
            valid_segments.append(seg)
    
    # If no valid segments, create a default "up" segment for the entire duration
    if not valid_segments:
        valid_segments = [{"start": 0, "end": duration, "status": "up"}]
    
    for seg in valid_segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        status = seg.get("status", "up")
        color = colors["up_segment"] if status == "up" else colors["down_segment"]
        segment_duration = end - start
        
        # Create multiple points along the segment for better hover coverage
        # Generate intermediate points every ~50 seconds for better hover interaction
        num_points = max(2, int((end - start) / 50) + 1)
        x_points = [start + (end - start) * i / (num_points - 1) for i in range(num_points)]
        y_points = [0] * num_points
        
        # Use Scatter with thick line and fill for better visibility
        fig.add_trace(
            go.Scatter(
                x=x_points,
                y=y_points,
                mode="lines",
                line=dict(color=color, width=40),  # 두꺼운 선으로 시각화
                fill="tozeroy",
                fillcolor=color,
                hovertemplate=(
                    f"Status: {'Up' if status == 'up' else 'Down'}<br>"
                    f"Duration: {segment_duration:.0f}s<br>"
                    f"Start: {start:.0f}s<br>"
                    f"End: {end:.0f}s"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )
    
    # Add legend indicators
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=10, color=colors["up_segment"]),
            name="Up",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=10, color=colors["down_segment"]),
            name="Down",
        )
    )
    
    fig.update_layout(
        height=100,  # 차트 높이 증가
        margin=dict(l=40, r=40, t=30, b=50),  # 하단 여백 증가 (b=50)로 X축 레이블 공간 확보
        xaxis=dict(
            title=dict(
                text="Time (seconds)",
                standoff=10,  # 레이블과 축 사이 간격
            ),
            range=[0, duration],
            showgrid=True,
            gridcolor=colors["grid"],
        ),
        yaxis=dict(
            showticklabels=False,
            range=[-0.3, 0.3],  # 좁은 범위로 선이 두껍게 보이도록
            showgrid=False,
            fixedrange=True,  # Y축 고정
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=11),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        dragmode=False,
    )
    
    return fig


# =============================================================================
# 미사용 함수 삭제 (2026-01-20)
# - create_pps_chart(): create_communication_chart()에 통합됨
# - create_jitter_chart(): create_communication_chart()에 통합됨
# =============================================================================
