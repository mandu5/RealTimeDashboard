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

from ..utils.helpers import get_chart_colors
from ..config import config


def create_communication_chart(
    data: List[Dict],
    p95: float,
    p99: float
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
        
    Returns:
        Plotly Figure object
        
    Example:
        >>> data = [
        ...     {"timestamp": "14:32:05", "pps": 1024, "jitter": 1.5},
        ...     ...
        ... ]
        >>> fig = create_communication_chart(data, 2.1, 2.4)
    """
    colors = get_chart_colors()
    
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("패킷 수신율 (PPS)", "지터 (Jitter, ms)"),
        vertical_spacing=0.12,
        row_heights=[0.5, 0.5],
    )
    
    # Extract data series
    timestamps = [d.get("timestamp", "") for d in data]
    pps_values = [d.get("pps", 0) for d in data]
    jitter_values = [d.get("jitter", 0) for d in data]
    
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
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=colors["grid"])
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=colors["grid"])
    
    # Layout configuration
    fig.update_layout(
        height=400,
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=11),
        showlegend=False,
        hovermode="x unified",
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
    
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        status = seg.get("status", "up")
        color = colors["up_segment"] if status == "up" else colors["down_segment"]
        segment_duration = end - start
        
        fig.add_trace(
            go.Scatter(
                x=[start, end],
                y=[1, 1],
                mode="lines",
                line=dict(color=color, width=24),
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
        height=80,
        margin=dict(l=40, r=40, t=20, b=20),
        xaxis=dict(
            title="Time (seconds)",
            range=[0, duration],
            showgrid=True,
            gridcolor=colors["grid"],
        ),
        yaxis=dict(
            showticklabels=False,
            range=[0, 2],
            showgrid=False,
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
    )
    
    return fig


def create_pps_chart(data: List[Dict]) -> go.Figure:
    """
    Create standalone PPS time series chart.
    
    Simplified single chart for PPS monitoring with range selector.
    
    Args:
        data: List of dictionaries with 'timestamp', 'pps' keys
        
    Returns:
        Plotly Figure object
    """
    colors = get_chart_colors()
    
    timestamps = [d.get("timestamp", "") for d in data]
    pps_values = [d.get("pps", 0) for d in data]
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=pps_values,
            mode="lines",
            name="PPS",
            line=dict(color=colors["primary"], width=2),
            fill="tozeroy",
            fillcolor=colors["fill_primary"],
        )
    )
    
    fig.update_layout(
        height=200,
        margin=dict(l=40, r=20, t=20, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=11),
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor=colors["grid"]),
        yaxis=dict(showgrid=True, gridcolor=colors["grid"], title="PPS"),
    )
    
    return fig


def create_jitter_chart(
    data: List[Dict],
    p95: float,
    p99: float
) -> go.Figure:
    """
    Create standalone jitter time series chart with reference lines.
    
    Args:
        data: List of dictionaries with 'timestamp', 'jitter' keys
        p95: Current P95 jitter value (ms)
        p99: Current P99 jitter value (ms)
        
    Returns:
        Plotly Figure object
    """
    colors = get_chart_colors()
    
    timestamps = [d.get("timestamp", "") for d in data]
    jitter_values = [d.get("jitter", 0) for d in data]
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=jitter_values,
            mode="lines",
            name="Jitter",
            line=dict(color=colors["secondary"], width=2),
            fill="tozeroy",
            fillcolor=colors["fill_secondary"],
        )
    )
    
    # Reference lines
    fig.add_hline(y=p95, line_dash="dash", line_color=colors["p95_line"],
                  annotation_text=f"P95: {p95}ms")
    fig.add_hline(y=p99, line_dash="dash", line_color=colors["p99_line"],
                  annotation_text=f"P99: {p99}ms")
    
    fig.update_layout(
        height=200,
        margin=dict(l=40, r=20, t=20, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=11),
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor=colors["grid"]),
        yaxis=dict(showgrid=True, gridcolor=colors["grid"], title="Jitter (ms)"),
    )
    
    return fig
