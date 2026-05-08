import pytest
from ugv_mon.ui.layouts.charts import create_communication_chart
from ugv_mon.ui.ml.anomaly_3d import create_anomaly_3d_scatter

def test_communication_chart_creation() -> None:
    data = [{"timestamp": "12:00:00", "pps": 10, "jitter": 5}]
    fig = create_communication_chart(data, p95=10)
    
    # Check if the figure is successfully created and has data
    assert fig is not None
    assert len(fig.data) >= 1


def test_anomaly_3d_creation() -> None:
    records = [{"jitter_current": 5, "pps": 10, "loss_rate": 0, "timestamp": "12:00"}]
    fig = create_anomaly_3d_scatter(records)

    # Check if the figure is successfully created and has data
    assert fig is not None
    assert len(fig.data) >= 1

