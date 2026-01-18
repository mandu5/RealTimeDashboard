"""
Log Table Component for UGV-MON Dashboard.

Implements the event log table using dash-ag-grid for
high-performance scrolling and enterprise features.
"""

from dash import html
import dash_ag_grid as dag
from typing import Dict, List


def get_log_column_defs() -> List[Dict]:
    """
    Get AG-Grid column definitions for the log table.
    
    Returns:
        List of column definition dictionaries
    """
    return [
        {
            "headerName": "Time",
            "field": "time",
            "width": 100,
            "pinned": "left",
            "cellStyle": {"fontFamily": "monospace"},
        },
        {
            "headerName": "Seq",
            "field": "seq",
            "width": 80,
            "type": "numericColumn",
            "cellStyle": {"fontFamily": "monospace"},
        },
        {
            "headerName": "Msg Code",
            "field": "msg_code",
            "width": 90,
            "cellStyle": {"fontFamily": "monospace"},
        },
        {
            "headerName": "Parse",
            "field": "parse_ok",
            "width": 70,
            "cellStyle": {
                "styleConditions": [
                    {
                        "condition": "params.value === '✗'",
                        "style": {"backgroundColor": "#fee2e2", "color": "#991b1b"},
                    },
                    {
                        "condition": "params.value === '✓'",
                        "style": {"color": "#065f46"},
                    },
                ],
            },
        },
        {
            "headerName": "Checksum",
            "field": "checksum_ok",
            "width": 90,
            "cellStyle": {
                "styleConditions": [
                    {
                        "condition": "params.value === '✗'",
                        "style": {"backgroundColor": "#fee2e2", "color": "#991b1b"},
                    },
                    {
                        "condition": "params.value === '✓'",
                        "style": {"color": "#065f46"},
                    },
                ],
            },
        },
        {
            "headerName": "Mode",
            "field": "mode",
            "width": 150,
            "flex": 1,
        },
        {
            "headerName": "Authority",
            "field": "authority",
            "width": 140,
        },
        {
            "headerName": "Notes",
            "field": "notes",
            "width": 200,
            "flex": 2,
            "cellStyle": {
                "styleConditions": [
                    {
                        "condition": "params.value && params.value.length > 0",
                        "style": {"backgroundColor": "#fef3c7", "color": "#92400e"},
                    },
                ],
            },
        },
    ]


def create_log_table(
    row_data: List[Dict],
    table_id: str = "log-table"
) -> dag.AgGrid:
    """
    Create the AG-Grid log table component.
    
    Displays packet log entries with columns:
    - Time: Packet timestamp (HH:MM:SS.mmm)
    - Seq: Sequence number from ICD
    - Msg Code: Message code from ICD header
    - Parse: Parse success indicator (✓/✗)
    - Checksum: Checksum verification (✓/✗)
    - Mode: Current operation mode
    - Authority: Current authority holder
    - Notes: Anomaly notes (jitter, loss, etc.)
    
    Args:
        row_data: List of log entry dictionaries
        table_id: Component ID for callbacks
        
    Returns:
        AG-Grid component configured for log display
        
    Example:
        >>> logs = [
        ...     {"time": "14:32:05.123", "seq": 49195, "msg_code": "0x01", ...},
        ...     ...
        ... ]
        >>> table = create_log_table(logs)
    """
    return dag.AgGrid(
        id=table_id,
        rowData=row_data,
        columnDefs=get_log_column_defs(),
        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "cellStyle": {
                "fontSize": "12px",
                "fontFamily": "Inter, sans-serif",
            },
        },
        dashGridOptions={
            "animateRows": True,
            "rowSelection": "single",
            "pagination": False,
            "domLayout": "normal",
            "suppressCellFocus": True,
            "suppressScrollOnNewData": False,  # Allow scrolling on data update
            "getRowStyle": {
                "styleConditions": [
                    {
                        "condition": "params.node.rowIndex === 0",
                        "style": {
                            "backgroundColor": "#dbeafe",
                            "borderLeft": "3px solid #3b82f6",
                        },
                    },
                ],
            },
        },
        style={
            "height": "400px",
            "width": "100%",
        },
        className="ag-theme-alpine",
    )


def create_log_table_header(log_count: int) -> html.Div:
    """
    Create the log table header with title and controls.
    
    Args:
        log_count: Current number of log entries
        
    Returns:
        Header div with title and control buttons
    """
    import dash_mantine_components as dmc
    
    return html.Div(
        children=[
            # Title section
            html.Div(
                children=[
                    html.Div(
                        style={
                            "width": "4px",
                            "height": "16px",
                            "backgroundColor": "#9333ea",
                            "borderRadius": "9999px",
                        }
                    ),
                    html.Div(
                        id="log-table-title",
                        children=f"로그/이벤트 테이블 (최근 {log_count}개)",
                        style={
                            "fontSize": "14px",
                            "fontWeight": "600",
                            "color": "#334155",
                        }
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                }
            ),
            # Control buttons
            html.Div(
                children=[
                    dmc.Button(
                        "Pause",
                        id="pause-btn",
                        variant="outline",
                        size="xs",
                    ),
                    dmc.Button(
                        "Clear",
                        id="clear-btn",
                        variant="outline",
                        size="xs",
                        color="red",
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "8px",
                }
            ),
        ],
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "16px",
        }
    )
