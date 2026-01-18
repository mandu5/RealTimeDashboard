"""
Dash callback handlers for UGV-MON Dashboard.

Callbacks are responsible for:
- Polling data updates via dcc.Interval
- UI state management (pause, auto-scroll)
- Component updates based on data changes
"""

from .update_callbacks import register_callbacks

__all__ = ["register_callbacks"]
