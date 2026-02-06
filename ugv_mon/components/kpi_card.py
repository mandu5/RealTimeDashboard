"""
KPI Card Component for UGV-MON Dashboard.

핵심 성능 지표를 카드 형식으로 표시합니다.
"""

from dash import html
import dash_mantine_components as dmc

from ..styles import VALUE_LARGE, UNIT_SMALL, LABEL_SMALL


def create_kpi_card(
    title: str,
    value,
    unit: str = "",
    show_progress: bool = False,
    progress_value: float = 0,
    progress_color: str = "blue"
) -> dmc.Card:
    """KPI 카드 컴포넌트."""
    value_display = [html.Span(str(value), style=VALUE_LARGE)]
    if unit:
        value_display.append(html.Span(f" {unit}", style=UNIT_SMALL))
    
    content = [
        html.Div(title, style=LABEL_SMALL),
        html.Div(value_display),
    ]
    
    if show_progress:
        content.append(dmc.Progress(value=min(progress_value, 100), color=progress_color, size="sm", style={"marginTop": "8px"}))
    
    return dmc.Card(children=[html.Div(content)], withBorder=True, p="md", radius="md", style={"height": "100%"})


def create_kpi_cards_row(data: dict) -> list:
    """7개 KPI 카드 생성."""
    return [
        create_kpi_card("수신 PPS", data.get("capturePps", 0), "pps", True, 70, "blue"),
        create_kpi_card("필터 통과율", data.get("filterPass", 0), "%", True, data.get("filterPass", 0), "green"),
        create_kpi_card("파싱 성공률", data.get("parseSuccess", 0), "%", True, data.get("parseSuccess", 0), "green"),
        create_kpi_card("체크섬 오류율", data.get("checksumFail", 0), "%"),
        create_kpi_card("추정 패킷 손실", data.get("packetLoss", 0), "pkts"),
        create_kpi_card("가용성 (5분)", data.get("availability", 0), "%", True, data.get("availability", 0), "green"),
        create_kpi_card("지터 (현재)", data.get("jitterCurrent", 0), "ms"),
        create_kpi_card("지터 (P95)", data.get("jitterP95", 0), "ms"),
    ]
