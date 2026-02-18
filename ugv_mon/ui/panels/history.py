"""연결 이력 패널 + 운용모드 전이 패널."""

import dash_mantine_components as dmc

from ._common import _build_list_content, _create_content_card, _format_iso_timestamp


def create_connection_history_panel(data: dict) -> dmc.Card:
    """연결 상태 변경 이력 패널."""
    return _create_content_card(
        "연결 이력",
        create_connection_history_content(data),
        "connection-history-container",
    )


def _connection_history_row(item: dict) -> dmc.Group:
    """연결 이력 단일 행."""
    status = "연결" if item.get("connected") else "끊김"
    color = "green" if item.get("connected") else "red"
    duration = item.get("duration")
    duration_str = f"({duration:.0f}초)" if duration else ""
    return dmc.Group([
        dmc.Badge(status, color=color, size="sm"),
        dmc.Text(_format_iso_timestamp(item.get("timestamp", "")), size="xs", c="dimmed"),
        dmc.Text(duration_str, size="xs", c="dimmed"),
    ], spacing="xs")


def create_connection_history_content(data: dict) -> list:
    """연결 이력 컨텐츠 (콜백에서도 사용)."""
    return _build_list_content(
        data.get("connectionHistory", []),
        "연결 이력 없음",
        _connection_history_row,
    )


def create_mode_transitions_panel(data: dict) -> dmc.Card:
    """운용 모드 전이 이력 패널."""
    return _create_content_card(
        "운용모드 전이",
        create_mode_transitions_content(data),
        "mode-transitions-container",
    )


def _mode_transition_row(t: dict) -> dmc.Group:
    """모드 전이 단일 행."""
    return dmc.Group([
        dmc.Text(t.get("from", "?"), size="sm", fw=500),
        dmc.Text("->", size="sm", c="dimmed"),
        dmc.Text(t.get("to", "?"), size="sm", fw=500),
        dmc.Text(_format_iso_timestamp(t.get("timestamp", "")), size="xs", c="dimmed"),
    ], spacing="xs")


def create_mode_transitions_content(data: dict) -> list:
    """운용모드 전이 컨텐츠 (콜백에서도 사용)."""
    return _build_list_content(
        data.get("modeTransitions", []),
        "모드 전이 없음",
        _mode_transition_row,
    )
